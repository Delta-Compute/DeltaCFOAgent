#!/usr/bin/env python3
"""
Notification Manager for Crypto Invoice System
Coordinates email notifications for invoice and payment events
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime, date
from jinja2 import Environment, FileSystemLoader
import os


logger = logging.getLogger(__name__)


class NotificationManager:
    """
    Manages email notifications for invoice system
    Renders templates and coordinates with EmailService
    """

    def __init__(self, email_service, db_manager, base_url: str):
        """
        Initialize notification manager

        Args:
            email_service: EmailService instance
            db_manager: Database manager
            base_url: Base URL for payment links (e.g., https://deltacfo.com)
        """
        self.email_service = email_service
        self.db_manager = db_manager
        self.base_url = base_url.rstrip('/')

        # Setup Jinja2 template environment
        template_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'templates'
        )
        self.jinja_env = Environment(loader=FileSystemLoader(template_dir))

        logger.info(f"Notification manager initialized with base URL: {base_url}")

    def _render_template(self, template_name: str, context: Dict[str, Any]) -> str:
        """
        Render email template with context

        Args:
            template_name: Template filename (e.g., 'email/invoice_created.html')
            context: Template context variables

        Returns:
            Rendered HTML string
        """
        try:
            # Add common context variables
            context['settings_url'] = f"{self.base_url}/email-settings"

            template = self.jinja_env.get_template(template_name)
            return template.render(**context)

        except Exception as e:
            logger.error(f"Error rendering template {template_name}: {e}")
            raise

    def notify_invoice_created(self, invoice_id: int, user_id: int = 1) -> Dict[str, Any]:
        """
        Send notification when invoice is created

        Args:
            invoice_id: Invoice ID
            user_id: User ID (default: 1 for Delta Energy)

        Returns:
            Dict with success status
        """
        try:
            # Get invoice details
            invoice = self.db_manager.get_invoice(invoice_id)
            if not invoice:
                return {'success': False, 'error': 'Invoice not found'}

            # Calculate total with fees and taxes
            base_amount = float(invoice.get('amount_usd', 0))
            fee_percent = float(invoice.get('transaction_fee_percent', 0))
            tax_percent = float(invoice.get('tax_percent', 0))
            fee_amount = base_amount * (fee_percent / 100)
            tax_amount = base_amount * (tax_percent / 100)
            invoice['total_amount'] = base_amount + fee_amount + tax_amount

            # Build payment URL
            payment_url = f"{self.base_url}/pay/{invoice['invoice_number']}"

            # Render template
            html_body = self._render_template('email/invoice_created.html', {
                'invoice': invoice,
                'payment_url': payment_url,
                'subject': f"New Invoice Created: {invoice['invoice_number']}"
            })

            # Send notification
            result = self.email_service.send_notification(
                user_id=user_id,
                notification_type='invoice_created',
                subject=f"New Invoice Created: {invoice['invoice_number']}",
                html_body=html_body,
                invoice_id=invoice_id
            )

            logger.info(f"Invoice created notification sent for {invoice['invoice_number']}")
            return result

        except Exception as e:
            logger.error(f"Error sending invoice created notification: {e}", exc_info=True)
            return {'success': False, 'error': str(e)}

    def notify_payment_detected(
        self,
        invoice_id: int,
        payment_data: Dict[str, Any],
        user_id: int = 1
    ) -> Dict[str, Any]:
        """
        Send notification when payment is first detected on blockchain

        Args:
            invoice_id: Invoice ID
            payment_data: Payment transaction data
            user_id: User ID

        Returns:
            Dict with success status
        """
        try:
            invoice = self.db_manager.get_invoice(invoice_id)
            if not invoice:
                return {'success': False, 'error': 'Invoice not found'}

            # Calculate total amount
            base_amount = float(invoice.get('amount_usd', 0))
            fee_percent = float(invoice.get('transaction_fee_percent', 0))
            tax_percent = float(invoice.get('tax_percent', 0))
            invoice['total_amount'] = base_amount * (1 + fee_percent/100 + tax_percent/100)

            payment_url = f"{self.base_url}/pay/{invoice['invoice_number']}"

            # Add estimated confirmation time based on network
            confirmation_times = {
                'BTC': '30-60 minutes',
                'ETH': '5-15 minutes',
                'ERC20': '5-15 minutes',
                'BEP20': '1-3 minutes',
                'TRC20': '1-3 minutes',
                'POLYGON': '1-2 minutes',
                'ARBITRUM': '1-2 minutes',
                'BASE': '1-2 minutes',
                'TAO': '5-10 minutes'
            }
            payment_data['estimated_time'] = confirmation_times.get(
                invoice.get('crypto_network', '').upper(),
                '10-20 minutes'
            )

            html_body = self._render_template('email/payment_detected.html', {
                'invoice': invoice,
                'payment': payment_data,
                'payment_url': payment_url,
                'subject': f"Payment Detected: {invoice['invoice_number']}"
            })

            result = self.email_service.send_notification(
                user_id=user_id,
                notification_type='payment_detected',
                subject=f"💰 Payment Detected: {invoice['invoice_number']}",
                html_body=html_body,
                invoice_id=invoice_id
            )

            logger.info(f"Payment detected notification sent for {invoice['invoice_number']}")
            return result

        except Exception as e:
            logger.error(f"Error sending payment detected notification: {e}", exc_info=True)
            return {'success': False, 'error': str(e)}

    def notify_payment_confirmed(
        self,
        invoice_id: int,
        payment_data: Dict[str, Any],
        user_id: int = 1
    ) -> Dict[str, Any]:
        """
        Send notification when payment is fully confirmed

        Args:
            invoice_id: Invoice ID
            payment_data: Payment transaction data
            user_id: User ID

        Returns:
            Dict with success status
        """
        try:
            invoice = self.db_manager.get_invoice(invoice_id)
            if not invoice:
                return {'success': False, 'error': 'Invoice not found'}

            # Calculate total amount
            base_amount = float(invoice.get('amount_usd', 0))
            fee_percent = float(invoice.get('transaction_fee_percent', 0))
            tax_percent = float(invoice.get('tax_percent', 0))
            invoice['total_amount'] = base_amount * (1 + fee_percent/100 + tax_percent/100)

            invoice_url = f"{self.base_url}/pay/{invoice['invoice_number']}"

            html_body = self._render_template('email/payment_confirmed.html', {
                'invoice': invoice,
                'payment': payment_data,
                'invoice_url': invoice_url,
                'subject': f"Payment Confirmed: {invoice['invoice_number']}"
            })

            result = self.email_service.send_notification(
                user_id=user_id,
                notification_type='payment_confirmed',
                subject=f"✅ Payment Confirmed: {invoice['invoice_number']}",
                html_body=html_body,
                invoice_id=invoice_id
            )

            logger.info(f"Payment confirmed notification sent for {invoice['invoice_number']}")
            return result

        except Exception as e:
            logger.error(f"Error sending payment confirmed notification: {e}", exc_info=True)
            return {'success': False, 'error': str(e)}

    def notify_partial_payment(
        self,
        invoice_id: int,
        payment_data: Dict[str, Any],
        shortfall_data: Dict[str, Any],
        user_id: int = 1
    ) -> Dict[str, Any]:
        """
        Send notification when partial payment is received

        Args:
            invoice_id: Invoice ID
            payment_data: Payment transaction data
            shortfall_data: Shortfall details
            user_id: User ID

        Returns:
            Dict with success status
        """
        try:
            invoice = self.db_manager.get_invoice(invoice_id)
            if not invoice:
                return {'success': False, 'error': 'Invoice not found'}

            # Calculate total amount
            base_amount = float(invoice.get('amount_usd', 0))
            fee_percent = float(invoice.get('transaction_fee_percent', 0))
            tax_percent = float(invoice.get('tax_percent', 0))
            invoice['total_amount'] = base_amount * (1 + fee_percent/100 + tax_percent/100)

            payment_url = f"{self.base_url}/pay/{invoice['invoice_number']}"

            html_body = self._render_template('email/partial_payment.html', {
                'invoice': invoice,
                'payment': payment_data,
                'shortfall': shortfall_data,
                'payment_url': payment_url,
                'subject': f"Partial Payment: {invoice['invoice_number']}"
            })

            result = self.email_service.send_notification(
                user_id=user_id,
                notification_type='partial_payment',
                subject=f"⚠️ Partial Payment Received: {invoice['invoice_number']}",
                html_body=html_body,
                invoice_id=invoice_id
            )

            logger.info(f"Partial payment notification sent for {invoice['invoice_number']}")
            return result

        except Exception as e:
            logger.error(f"Error sending partial payment notification: {e}", exc_info=True)
            return {'success': False, 'error': str(e)}

    def notify_overpayment(
        self,
        invoice_id: int,
        payment_data: Dict[str, Any],
        overpayment_data: Dict[str, Any],
        user_id: int = 1
    ) -> Dict[str, Any]:
        """
        Send notification when overpayment is received

        Args:
            invoice_id: Invoice ID
            payment_data: Payment transaction data
            overpayment_data: Overpayment details
            user_id: User ID

        Returns:
            Dict with success status
        """
        try:
            invoice = self.db_manager.get_invoice(invoice_id)
            if not invoice:
                return {'success': False, 'error': 'Invoice not found'}

            # Calculate total amount
            base_amount = float(invoice.get('amount_usd', 0))
            fee_percent = float(invoice.get('transaction_fee_percent', 0))
            tax_percent = float(invoice.get('tax_percent', 0))
            invoice['total_amount'] = base_amount * (1 + fee_percent/100 + tax_percent/100)

            payment_url = f"{self.base_url}/pay/{invoice['invoice_number']}"

            html_body = self._render_template('email/overpayment.html', {
                'invoice': invoice,
                'payment': payment_data,
                'overpayment': overpayment_data,
                'payment_url': payment_url,
                'refund_address': invoice.get('client_wallet_address'),
                'subject': f"Overpayment: {invoice['invoice_number']}"
            })

            result = self.email_service.send_notification(
                user_id=user_id,
                notification_type='overpayment',
                subject=f"💰 Overpayment Received: {invoice['invoice_number']}",
                html_body=html_body,
                invoice_id=invoice_id
            )

            logger.info(f"Overpayment notification sent for {invoice['invoice_number']}")
            return result

        except Exception as e:
            logger.error(f"Error sending overpayment notification: {e}", exc_info=True)
            return {'success': False, 'error': str(e)}

    def notify_invoice_expired(self, invoice_id: int, user_id: int = 1) -> Dict[str, Any]:
        """
        Send notification when invoice expires without payment

        Args:
            invoice_id: Invoice ID
            user_id: User ID

        Returns:
            Dict with success status
        """
        try:
            invoice = self.db_manager.get_invoice(invoice_id)
            if not invoice:
                return {'success': False, 'error': 'Invoice not found'}

            # Calculate total amount
            base_amount = float(invoice.get('amount_usd', 0))
            fee_percent = float(invoice.get('transaction_fee_percent', 0))
            tax_percent = float(invoice.get('tax_percent', 0))
            invoice['total_amount'] = base_amount * (1 + fee_percent/100 + tax_percent/100)

            # Calculate days overdue
            try:
                due_date = datetime.strptime(invoice['due_date'], '%Y-%m-%d').date()
                days_overdue = (date.today() - due_date).days
            except:
                days_overdue = 0

            invoice_url = f"{self.base_url}/pay/{invoice['invoice_number']}"

            # Get client contact if available
            client_contact = None
            if invoice.get('client_contact'):
                client_contact = {
                    'email': invoice['client_contact']
                }

            html_body = self._render_template('email/invoice_expired.html', {
                'invoice': invoice,
                'days_overdue': days_overdue,
                'invoice_url': invoice_url,
                'client_contact': client_contact,
                'subject': f"Invoice Expired: {invoice['invoice_number']}"
            })

            result = self.email_service.send_notification(
                user_id=user_id,
                notification_type='invoice_expired',
                subject=f"⏰ Invoice Expired: {invoice['invoice_number']}",
                html_body=html_body,
                invoice_id=invoice_id
            )

            logger.info(f"Invoice expired notification sent for {invoice['invoice_number']}")
            return result

        except Exception as e:
            logger.error(f"Error sending invoice expired notification: {e}", exc_info=True)
            return {'success': False, 'error': str(e)}

    def notify_client_invoice_sent(
        self,
        invoice_id: int,
        recipient_email: str,
        user_id: int = 1
    ) -> Dict[str, Any]:
        """
        Send notification when invoice is sent to client

        Args:
            invoice_id: Invoice ID
            recipient_email: Client's email address
            user_id: User ID

        Returns:
            Dict with success status
        """
        try:
            invoice = self.db_manager.get_invoice(invoice_id)
            if not invoice:
                return {'success': False, 'error': 'Invoice not found'}

            # Calculate total amount
            base_amount = float(invoice.get('amount_usd', 0))
            fee_percent = float(invoice.get('transaction_fee_percent', 0))
            tax_percent = float(invoice.get('tax_percent', 0))
            invoice['total_amount'] = base_amount * (1 + fee_percent/100 + tax_percent/100)

            payment_url = f"{self.base_url}/pay/{invoice['invoice_number']}"

            # Confirmation time based on network
            confirmation_times = {
                'BTC': '30-60 minutes',
                'ETH': '5-15 minutes',
                'ERC20': '5-15 minutes',
                'BEP20': '1-3 minutes',
                'TRC20': '1-3 minutes',
                'POLYGON': '1-2 minutes',
                'ARBITRUM': '1-2 minutes',
                'BASE': '1-2 minutes',
                'TAO': '5-10 minutes'
            }
            confirmation_time = confirmation_times.get(
                invoice.get('crypto_network', '').upper(),
                '10-20 minutes'
            )

            html_body = self._render_template('email/client_invoice_sent.html', {
                'invoice': invoice,
                'recipient_email': recipient_email,
                'payment_url': payment_url,
                'sent_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'confirmation_time': confirmation_time,
                'subject': f"Invoice Sent to Client: {invoice['invoice_number']}"
            })

            result = self.email_service.send_notification(
                user_id=user_id,
                notification_type='client_invoice_sent',
                subject=f"📧 Invoice Sent: {invoice['invoice_number']}",
                html_body=html_body,
                invoice_id=invoice_id
            )

            logger.info(f"Client invoice sent notification for {invoice['invoice_number']}")
            return result

        except Exception as e:
            logger.error(f"Error sending client invoice sent notification: {e}", exc_info=True)
            return {'success': False, 'error': str(e)}
