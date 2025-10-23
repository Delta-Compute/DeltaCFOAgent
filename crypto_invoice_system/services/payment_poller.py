#!/usr/bin/env python3
"""
Payment Polling Service
Continuously polls MEXC API every 30 seconds to detect crypto payments
"""

import time
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Any
import logging
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.mexc_service import MEXCService, MEXCAPIError
from models.database_postgresql import CryptoInvoiceDatabaseManager, InvoiceStatus, PaymentStatus
from services.amount_based_matcher import AmountBasedPaymentMatcher
from services.blockchain_explorer import BlockchainExplorer


class PaymentPoller:
    """
    Automated payment detection service
    Polls MEXC API at regular intervals to detect incoming payments
    """

    def __init__(self, mexc_service: MEXCService, db_manager: CryptoInvoiceDatabaseManager,
                 poll_interval: int = 30, payment_callback: Callable = None,
                 amount_matcher: AmountBasedPaymentMatcher = None,
                 blockchain_explorer: BlockchainExplorer = None,
                 notification_manager = None):
        """
        Initialize payment poller

        Args:
            mexc_service: MEXC API service instance
            db_manager: CryptoInvoiceDatabaseManager instance for PostgreSQL
            poll_interval: Polling interval in seconds (default 30)
            payment_callback: Optional callback function when payment detected
            amount_matcher: Amount-based matcher for shared addresses
            blockchain_explorer: BlockchainExplorer instance for direct blockchain verification
            notification_manager: NotificationManager instance for email notifications
        """
        self.mexc = mexc_service
        self.db = db_manager
        self.poll_interval = poll_interval
        self.payment_callback = payment_callback
        self.amount_matcher = amount_matcher or AmountBasedPaymentMatcher(tolerance_percent=0.1)
        self.blockchain_explorer = blockchain_explorer or BlockchainExplorer()
        self.notification_manager = notification_manager

        self.is_running = False
        self.polling_thread = None

        # Setup logging
        self.logger = logging.getLogger("PaymentPoller")
        self.logger.setLevel(logging.INFO)

        # Statistics
        self.stats = {
            "total_polls": 0,
            "payments_detected": 0,
            "payments_confirmed": 0,
            "errors": 0,
            "last_poll_time": None
        }

    def start(self):
        """Start the polling service in a background thread"""
        if self.is_running:
            self.logger.warning("Polling service already running")
            return

        self.is_running = True
        self.polling_thread = threading.Thread(target=self._polling_loop, daemon=True)
        self.polling_thread.start()
        self.logger.info(f"Payment polling service started (interval: {self.poll_interval}s)")

    def stop(self):
        """Stop the polling service"""
        if not self.is_running:
            return

        self.is_running = False
        if self.polling_thread:
            self.polling_thread.join(timeout=5)
        self.logger.info("Payment polling service stopped")

    def _polling_loop(self):
        """Main polling loop - runs in background thread"""
        while self.is_running:
            try:
                self._poll_pending_invoices()
                self.stats["total_polls"] += 1
                self.stats["last_poll_time"] = datetime.now()
            except Exception as e:
                self.logger.error(f"Error in polling loop: {e}")
                self.stats["errors"] += 1

            # Wait for next poll interval
            time.sleep(self.poll_interval)

    def _poll_pending_invoices(self):
        """Poll all pending invoices for payment detection"""
        # Get all unpaid invoices
        pending_invoices = self.db.get_pending_invoices()

        if not pending_invoices:
            self.logger.debug("No pending invoices to poll")
            return

        self.logger.info(f"Polling {len(pending_invoices)} pending invoices")

        for invoice in pending_invoices:
            try:
                # Check if invoice has expired first
                if self._check_invoice_expiration(invoice):
                    continue  # Skip payment check for expired invoices

                # Check for payment
                self._check_invoice_payment(invoice)
            except Exception as e:
                self.logger.error(f"Error checking invoice {invoice['invoice_number']}: {e}")
                self.db.log_polling_event(
                    invoice_id=invoice['id'],
                    status='error',
                    error_message=str(e)
                )

    def _check_invoice_expiration(self, invoice: Dict) -> bool:
        """
        Check if invoice has expired and mark as EXPIRED if needed

        Expiration Logic:
        - created_at + expiration_hours > now → invoice expired
        - Only mark EXPIRED if status is 'sent' (not already paid/cancelled)

        Args:
            invoice: Invoice record with expiration_hours field

        Returns:
            True if invoice was marked as expired, False otherwise
        """
        invoice_id = invoice['id']
        invoice_number = invoice['invoice_number']
        status = invoice['status']

        # Only check expiration for sent invoices
        if status not in ['sent', InvoiceStatus.SENT.value]:
            return False

        # Get expiration settings
        expiration_hours = int(invoice.get('expiration_hours', 24))
        created_at = invoice.get('created_at')

        if not created_at:
            self.logger.warning(f"Invoice {invoice_number}: No created_at timestamp, skipping expiration check")
            return False

        # Parse created_at if string
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)

        # Calculate expiration time
        expiration_time = created_at + timedelta(hours=expiration_hours)
        now = datetime.now()

        # Check if expired
        if now >= expiration_time:
            # Mark as expired
            time_expired = (now - expiration_time).total_seconds() / 3600  # hours
            self.logger.warning(
                f"⏰ Invoice {invoice_number} EXPIRED ({time_expired:.1f} hours past expiration). "
                f"Created: {created_at}, Expiration: {expiration_hours}h"
            )

            # Update status to EXPIRED
            self.db.update_invoice_status(
                invoice_id=invoice_id,
                status=InvoiceStatus.EXPIRED.value
            )

            # Log expiration event
            self.db.log_polling_event(
                invoice_id=invoice_id,
                status='expired',
                error_message=f"Invoice expired {time_expired:.1f} hours ago"
            )

            # Send invoice expired notification
            if self.notification_manager:
                try:
                    user_id = invoice.get('user_id', 1)
                    self.notification_manager.notify_invoice_expired(invoice_id, user_id)
                    self.logger.info(f"Invoice expired notification sent for {invoice_number}")
                except Exception as e:
                    self.logger.error(f"Error sending invoice expired notification: {e}")

            return True
        else:
            # Not expired yet - log remaining time
            time_remaining = (expiration_time - now).total_seconds() / 3600  # hours
            if time_remaining < 1:  # Less than 1 hour remaining
                self.logger.info(
                    f"Invoice {invoice_number} expires in {time_remaining * 60:.0f} minutes"
                )

            return False

    def _check_invoice_payment(self, invoice: Dict):
        """
        Check if payment has been received for a specific invoice
        Uses amount-based matching since we share deposit addresses

        Args:
            invoice: Invoice dictionary from database
        """
        invoice_id = invoice['id']
        invoice_number = invoice['invoice_number']
        expected_amount = invoice['crypto_amount']
        currency = invoice['crypto_currency']
        network = invoice['crypto_network']

        self.logger.debug(f"Checking invoice {invoice_number} for {expected_amount} {currency}/{network}")

        try:
            # Get all recent deposits for this currency
            issue_date = datetime.fromisoformat(invoice['issue_date'])
            start_time = max(issue_date, datetime.now() - timedelta(days=7))
            start_timestamp = int(start_time.timestamp() * 1000)

            deposits = self.mexc.get_deposit_history(
                currency=currency,
                start_time=start_timestamp,
                status=None  # Check all statuses
            )

            # Get existing payments to avoid duplicates
            existing_payments = self.db.get_payments_for_invoice(invoice_id)

            # Filter deposits for matching network and unprocessed
            for deposit in deposits:
                if deposit.get('network') != network:
                    continue

                deposit_amount = float(deposit.get('amount', 0))
                tx_hash = deposit.get('txId')

                # Skip if already processed
                if self.amount_matcher.detect_duplicate_payment(
                    deposit_amount, currency, network, tx_hash, existing_payments
                ):
                    continue

                # Check if amount matches this invoice
                # Apply rate lock validation
                expected_amount_to_use = self._get_expected_amount_with_rate_lock(invoice)

                min_amount = expected_amount_to_use * (1 - 0.001)  # 0.1% tolerance
                max_amount = expected_amount_to_use * (1 + 0.001)

                if min_amount <= deposit_amount <= max_amount:
                    # Found matching deposit!
                    deposit_info = {
                        'transaction_hash': tx_hash,
                        'amount': deposit_amount,
                        'currency': deposit.get('coin'),
                        'network': deposit.get('network'),
                        'confirmations': deposit.get('confirmations', 0),
                        'status': deposit.get('status'),
                        'timestamp': deposit.get('insertTime'),
                        'raw_data': deposit
                    }

                    deposit = deposit_info  # Reformat for compatibility
                    break
            else:
                deposit = None

            if deposit:
                self.logger.info(f"💰 Payment detected for invoice {invoice_number}!")
                self._handle_payment_detected(invoice, deposit)
                self.stats["payments_detected"] += 1

                # Log successful detection
                self.db.log_polling_event(
                    invoice_id=invoice_id,
                    status='payment_detected',
                    deposits_found=1,
                    api_response=str(deposit)
                )
            else:
                # No payment found yet
                self.db.log_polling_event(
                    invoice_id=invoice_id,
                    status='no_payment',
                    deposits_found=0
                )

        except MEXCAPIError as e:
            self.logger.error(f"MEXC API error for invoice {invoice_number}: {e}")
            self.db.log_polling_event(
                invoice_id=invoice_id,
                status='api_error',
                error_message=str(e)
            )

    def _handle_payment_detected(self, invoice: Dict, deposit: Dict):
        """
        Handle detected payment

        Args:
            invoice: Invoice record
            deposit: Deposit information from MEXC
        """
        invoice_id = invoice['id']
        invoice_number = invoice['invoice_number']

        # Check if payment already recorded
        existing_payments = self.db.get_payments_for_invoice(invoice_id)
        for payment in existing_payments:
            if payment['transaction_hash'] == deposit['transaction_hash']:
                self.logger.info(f"Payment already recorded for invoice {invoice_number}")
                return

        # Record payment transaction
        payment_data = {
            "invoice_id": invoice_id,
            "transaction_hash": deposit['transaction_hash'],
            "amount_received": deposit['amount'],
            "currency": deposit['currency'],
            "network": deposit['network'],
            "deposit_address": invoice['deposit_address'],
            "status": self._determine_payment_status(deposit),
            "confirmations": deposit.get('confirmations', 0),
            "required_confirmations": MEXCService.get_required_confirmations(
                deposit['currency'], deposit['network']
            ),
            "mexc_transaction_id": deposit.get('transaction_hash'),
            "raw_api_response": deposit.get('raw_data')
        }

        payment_id = self.db.create_payment_transaction(payment_data)
        self.logger.info(f"Payment transaction recorded (ID: {payment_id})")

        # Send payment detected notification
        if self.notification_manager:
            try:
                user_id = invoice.get('user_id', 1)
                payment_notification_data = {
                    'amount': deposit['amount'],
                    'currency': deposit['currency'],
                    'txid': deposit['transaction_hash'],
                    'confirmations': deposit.get('confirmations', 0),
                    'required_confirmations': payment_data['required_confirmations'],
                    'detected_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
                self.notification_manager.notify_payment_detected(
                    invoice_id, payment_notification_data, user_id
                )
                self.logger.info(f"Payment detected notification sent for {invoice_number}")
            except Exception as e:
                self.logger.error(f"Error sending payment detected notification: {e}")

        # Check if payment is confirmed
        if deposit.get('confirmations', 0) >= payment_data['required_confirmations']:
            self._confirm_payment(invoice, payment_id, deposit)
        else:
            # Update invoice status to partially paid
            self.db.update_invoice_status(invoice_id, InvoiceStatus.PARTIALLY_PAID.value)
            self.logger.info(f"Invoice {invoice_number} marked as partially paid (awaiting confirmations)")

        # Call payment callback if provided
        if self.payment_callback:
            try:
                self.payment_callback({
                    "event": "payment_detected",
                    "invoice": invoice,
                    "payment": deposit
                })
            except Exception as e:
                self.logger.error(f"Error in payment callback: {e}")

    def _determine_payment_status(self, deposit: Dict) -> str:
        """
        Determine payment status based on deposit info

        Args:
            deposit: Deposit information

        Returns:
            Payment status string
        """
        confirmations = deposit.get('confirmations', 0)
        required = MEXCService.get_required_confirmations(
            deposit['currency'], deposit['network']
        )

        if confirmations >= required:
            return PaymentStatus.CONFIRMED.value
        elif confirmations > 0:
            return PaymentStatus.DETECTED.value
        else:
            return PaymentStatus.PENDING.value

    def _confirm_payment(self, invoice: Dict, payment_id: int, deposit: Dict):
        """
        Confirm payment and reconcile total amount received

        Args:
            invoice: Invoice record
            payment_id: Payment transaction ID
            deposit: Deposit information
        """
        invoice_id = invoice['id']
        invoice_number = invoice['invoice_number']

        # Update payment status
        self.db.update_payment_confirmations(
            payment_id=payment_id,
            confirmations=deposit.get('confirmations', 0),
            status=PaymentStatus.CONFIRMED.value
        )

        # Reconcile all payments for this invoice
        self._reconcile_invoice_payments(invoice)

        self.stats["payments_confirmed"] += 1

        # Call payment callback for confirmation
        if self.payment_callback:
            try:
                self.payment_callback({
                    "event": "payment_confirmed",
                    "invoice": invoice,
                    "payment": deposit
                })
            except Exception as e:
                self.logger.error(f"Error in payment callback: {e}")

    def _reconcile_invoice_payments(self, invoice: Dict):
        """
        Reconcile all confirmed payments for an invoice and set appropriate status

        Handles:
        - Partial payments (underpayment)
        - Exact payments
        - Overpayments
        - Multiple payments to same invoice

        Args:
            invoice: Invoice dictionary
        """
        invoice_id = invoice['id']
        invoice_number = invoice['invoice_number']
        expected_amount = float(invoice['crypto_amount'])
        currency = invoice['crypto_currency']

        # Get all confirmed payments for this invoice
        all_payments = self.db.get_payments_for_invoice(invoice_id)
        confirmed_payments = [p for p in all_payments if p['status'] == PaymentStatus.CONFIRMED.value]

        if not confirmed_payments:
            self.logger.warning(f"No confirmed payments found for invoice {invoice_number}")
            return

        # Calculate total amount received
        total_received = sum(float(p['amount_received']) for p in confirmed_payments)

        # Determine tolerance based on currency type
        tolerance = 0.001 if currency in ['USDT', 'USDC', 'DAI', 'BUSD'] else 0.005
        min_amount = expected_amount * (1 - tolerance)
        max_amount = expected_amount * (1 + tolerance)

        self.logger.info(
            f"Payment reconciliation for {invoice_number}: "
            f"Expected={expected_amount}, Received={total_received} {currency}"
        )

        # Determine invoice status based on total received
        if total_received < min_amount:
            # PARTIAL payment (underpaid)
            shortage = expected_amount - total_received
            shortage_percent = (shortage / expected_amount) * 100

            self.logger.warning(
                f"⚠️  PARTIAL payment for {invoice_number}: "
                f"Received {total_received}/{expected_amount} {currency} "
                f"(shortage: {shortage:.8f} {currency}, {shortage_percent:.2f}%)"
            )

            self.db.update_invoice_status(
                invoice_id=invoice_id,
                status=InvoiceStatus.PARTIAL.value
            )

            # Log partial payment event
            self.db.log_polling_event(
                invoice_id=invoice_id,
                status='partial_payment',
                error_message=f"Underpaid by {shortage:.8f} {currency} ({shortage_percent:.2f}%)"
            )

            # Send partial payment notification
            if self.notification_manager:
                try:
                    user_id = invoice.get('user_id', 1)
                    payment_data = {
                        'amount': total_received,
                        'currency': currency,
                        'percentage': (total_received / expected_amount) * 100
                    }
                    shortfall_data = {
                        'amount': shortage,
                        'currency': currency,
                        'usd_value': shortage * float(invoice.get('exchange_rate', 1))
                    }
                    self.notification_manager.notify_partial_payment(
                        invoice_id, payment_data, shortfall_data, user_id
                    )
                    self.logger.info(f"Partial payment notification sent for {invoice_number}")
                except Exception as e:
                    self.logger.error(f"Error sending partial payment notification: {e}")

        elif total_received > max_amount:
            # OVERPAID
            overpayment = total_received - expected_amount
            overpayment_percent = (overpayment / expected_amount) * 100

            self.logger.warning(
                f"💰 OVERPAYMENT for {invoice_number}: "
                f"Received {total_received}/{expected_amount} {currency} "
                f"(overpayment: {overpayment:.8f} {currency}, {overpayment_percent:.2f}%)"
            )

            self.db.update_invoice_status(
                invoice_id=invoice_id,
                status=InvoiceStatus.OVERPAID.value,
                paid_at=datetime.now()
            )

            # Log overpayment event
            self.db.log_polling_event(
                invoice_id=invoice_id,
                status='overpayment',
                error_message=f"Overpaid by {overpayment:.8f} {currency} ({overpayment_percent:.2f}%)"
            )

            # Send overpayment notification
            if self.notification_manager:
                try:
                    user_id = invoice.get('user_id', 1)
                    payment_data = {
                        'amount': total_received,
                        'currency': currency,
                        'percentage': (total_received / expected_amount) * 100
                    }
                    overpayment_data = {
                        'amount': overpayment,
                        'currency': currency,
                        'usd_value': overpayment * float(invoice.get('exchange_rate', 1))
                    }
                    self.notification_manager.notify_overpayment(
                        invoice_id, payment_data, overpayment_data, user_id
                    )
                    self.logger.info(f"Overpayment notification sent for {invoice_number}")
                except Exception as e:
                    self.logger.error(f"Error sending overpayment notification: {e}")

            # TODO: Queue for refund processing
            # self._queue_refund(invoice, overpayment, currency)

        else:
            # PAID (within tolerance)
            self.logger.info(
                f"✅ Invoice {invoice_number} confirmed as PAID: "
                f"{total_received} {currency} (expected {expected_amount})"
            )

            self.db.update_invoice_status(
                invoice_id=invoice_id,
                status=InvoiceStatus.PAID.value,
                paid_at=datetime.now()
            )

            # Send payment confirmed notification
            if self.notification_manager:
                try:
                    user_id = invoice.get('user_id', 1)
                    payment_data = {
                        'amount': total_received,
                        'currency': currency,
                        'usd_value': total_received * float(invoice.get('exchange_rate', 1)),
                        'txid': confirmed_payments[0].get('transaction_hash', 'N/A'),
                        'confirmations': confirmed_payments[0].get('confirmations', 0),
                        'confirmed_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    }
                    self.notification_manager.notify_payment_confirmed(
                        invoice_id, payment_data, user_id
                    )
                    self.logger.info(f"Payment confirmed notification sent for {invoice_number}")
                except Exception as e:
                    self.logger.error(f"Error sending payment confirmed notification: {e}")

        # Log payment reconciliation
        payment_count = len(confirmed_payments)
        if payment_count > 1:
            self.logger.info(
                f"Invoice {invoice_number} paid with {payment_count} transactions: "
                f"{', '.join([p['transaction_hash'][:16] + '...' for p in confirmed_payments])}"
            )

    def _queue_refund(self, invoice: Dict, overpayment_amount: float, currency: str):
        """
        Queue overpayment for refund processing

        Args:
            invoice: Invoice dictionary
            overpayment_amount: Amount overpaid
            currency: Currency symbol

        Note: This is a placeholder for future refund automation
        """
        self.logger.info(
            f"🔄 Queuing refund for invoice {invoice['invoice_number']}: "
            f"{overpayment_amount:.8f} {currency}"
        )

        # TODO: Implement refund queue
        # - Store in refunds table
        # - Send notification to admin
        # - Optionally auto-refund to client_wallet_address
        pass

    def _get_expected_amount_with_rate_lock(self, invoice: Dict) -> float:
        """
        Get expected crypto amount considering rate lock mechanism

        Rate Lock Rules:
        - If within lock period (15 min): Use original crypto_amount
        - If outside lock period: Recalculate based on current exchange rate

        Args:
            invoice: Invoice record with rate_locked_until field

        Returns:
            Expected crypto amount to match against
        """
        original_crypto_amount = float(invoice['crypto_amount'])
        rate_locked_until = invoice.get('rate_locked_until')

        # If no rate lock set, use original amount
        if not rate_locked_until:
            self.logger.debug(f"Invoice {invoice['invoice_number']}: No rate lock set, using original amount")
            return original_crypto_amount

        # Parse rate lock expiration
        if isinstance(rate_locked_until, str):
            rate_locked_until = datetime.fromisoformat(rate_locked_until)

        # Check if rate lock is still valid
        now = datetime.now()
        if now <= rate_locked_until:
            # Within lock period - use original amount
            time_remaining = (rate_locked_until - now).total_seconds() / 60
            self.logger.info(
                f"Invoice {invoice['invoice_number']}: Rate lock active "
                f"({time_remaining:.1f} min remaining), using locked amount: {original_crypto_amount}"
            )
            return original_crypto_amount
        else:
            # Outside lock period - recalculate based on current rate
            time_expired = (now - rate_locked_until).total_seconds() / 60
            self.logger.warning(
                f"Invoice {invoice['invoice_number']}: Rate lock expired "
                f"({time_expired:.1f} min ago), recalculating amount at current rate"
            )

            # Get current exchange rate
            # Note: We need to calculate total amount first (base + fees + taxes)
            base_amount_usd = float(invoice['amount_usd'])
            fee_percent = float(invoice.get('transaction_fee_percent', 0))
            tax_percent = float(invoice.get('tax_percent', 0))

            fee_amount = base_amount_usd * (fee_percent / 100)
            tax_amount = base_amount_usd * (tax_percent / 100)
            total_amount_usd = base_amount_usd + fee_amount + tax_amount

            # Get current price from CoinGecko (simplified - would need proper price service)
            # For now, use original rate but log warning
            # TODO: Integrate with live price feed
            self.logger.warning(
                f"Invoice {invoice['invoice_number']}: Rate lock expired but live price "
                f"recalculation not yet implemented. Using original amount with tolerance."
            )

            # Use original amount but with wider tolerance to account for rate changes
            # This is a temporary solution until live price feed is integrated
            return original_crypto_amount

    def verify_transaction_on_chain(self, invoice: Dict, tx_hash: str) -> Optional[Dict]:
        """
        Verify transaction directly on blockchain using explorer APIs

        This is used for:
        - Manual transaction verification
        - Fallback when MEXC API fails
        - Direct blockchain confirmation tracking
        - Supporting chains not available on MEXC

        Args:
            invoice: Invoice dictionary
            tx_hash: Transaction hash to verify

        Returns:
            Transaction details if found and valid, None otherwise
        """
        invoice_id = invoice['id']
        invoice_number = invoice['invoice_number']
        currency = invoice['crypto_currency']
        network = invoice['crypto_network']
        expected_amount = float(invoice['crypto_amount'])
        deposit_address = invoice['deposit_address']

        self.logger.info(
            f"Verifying transaction on-chain for invoice {invoice_number}: "
            f"tx={tx_hash}, expected={expected_amount} {currency}/{network}"
        )

        try:
            # Use blockchain explorer to verify transaction
            tx_details = self.blockchain_explorer.verify_transaction(
                tx_hash=tx_hash,
                currency=currency,
                network=network,
                expected_amount=expected_amount,
                address=deposit_address
            )

            if not tx_details:
                self.logger.warning(
                    f"Transaction {tx_hash} not found on {network} blockchain"
                )
                return None

            # Check if amount matches (with tolerance)
            received_amount = tx_details.get('amount', 0)
            tolerance = 0.01 if currency in ['USDT', 'USDC', 'DAI', 'BUSD'] else 0.005
            min_amount = expected_amount * (1 - tolerance)
            max_amount = expected_amount * (1 + tolerance)

            if not (min_amount <= received_amount <= max_amount):
                self.logger.warning(
                    f"Amount mismatch for {tx_hash}: "
                    f"expected={expected_amount}, received={received_amount}"
                )
                # Still return the transaction but flag the mismatch
                tx_details['amount_mismatch'] = True

            # Log successful verification
            self.logger.info(
                f"✅ Transaction verified on-chain: {tx_hash} - "
                f"{received_amount} {currency} ({tx_details.get('confirmations', 0)} confirmations)"
            )

            return tx_details

        except Exception as e:
            self.logger.error(
                f"Error verifying transaction {tx_hash} on-chain: {e}"
            )
            return None

    def check_confirmations_update(self):
        """
        Check all detected payments for confirmation updates
        This should be called periodically to update confirmation counts
        """
        # Get all detected but unconfirmed payments
        conn = self.db.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT p.*, i.invoice_number, i.crypto_currency, i.deposit_address
            FROM payment_transactions p
            JOIN invoices i ON p.invoice_id = i.id
            WHERE p.status = 'detected'
            AND p.confirmations < p.required_confirmations
        """)

        unconfirmed_payments = [dict(row) for row in cursor.fetchall()]
        conn.close()

        self.logger.info(f"Checking confirmation updates for {len(unconfirmed_payments)} payments")

        for payment in unconfirmed_payments:
            try:
                # Try MEXC first for confirmation updates
                tx_info = None

                if self.mexc:
                    try:
                        tx_info = self.mexc.verify_transaction_manually(
                            txid=payment['transaction_hash'],
                            currency=payment['currency']
                        )
                    except Exception as e:
                        self.logger.warning(f"MEXC confirmation check failed: {e}")

                # Fallback to blockchain explorer
                if not tx_info:
                    invoice = self.db.get_invoice(payment['invoice_id'])
                    if invoice:
                        tx_info = self.blockchain_explorer.verify_transaction(
                            tx_hash=payment['transaction_hash'],
                            currency=payment['currency'],
                            network=payment['network'],
                            expected_amount=payment['amount_received'],
                            address=payment['deposit_address']
                        )

                if tx_info:
                    new_confirmations = tx_info.get('confirmations', 0)

                    if new_confirmations > payment['confirmations']:
                        self.logger.info(
                            f"Confirmation update for {payment['invoice_number']}: "
                            f"{new_confirmations}/{payment['required_confirmations']}"
                        )

                        # Update confirmation count
                        if new_confirmations >= payment['required_confirmations']:
                            # Payment now confirmed!
                            invoice = self.db.get_invoice(payment['invoice_id'])
                            self._confirm_payment(invoice, payment['id'], tx_info)
                        else:
                            self.db.update_payment_confirmations(
                                payment_id=payment['id'],
                                confirmations=new_confirmations
                            )

            except Exception as e:
                self.logger.error(f"Error checking confirmations for payment {payment['id']}: {e}")

    def manual_payment_verification(self, invoice_id: int, txid: str,
                                   verified_by: str) -> Dict[str, Any]:
        """
        Manually verify a payment by transaction ID

        Args:
            invoice_id: Invoice ID
            txid: Transaction ID/hash
            verified_by: Username of person verifying

        Returns:
            Verification result dictionary
        """
        invoice = self.db.get_invoice(invoice_id)
        if not invoice:
            return {"success": False, "error": "Invoice not found"}

        try:
            # Try MEXC verification first
            tx_info = None
            verification_source = None

            if self.mexc:
                try:
                    tx_info = self.mexc.verify_transaction_manually(
                        txid=txid,
                        currency=invoice['crypto_currency']
                    )
                    if tx_info:
                        verification_source = "MEXC"
                except Exception as e:
                    self.logger.warning(f"MEXC verification failed: {e}, trying blockchain explorer")

            # Fallback to blockchain explorer if MEXC fails or unavailable
            if not tx_info:
                self.logger.info(f"Using blockchain explorer for verification of {txid}")
                tx_info = self.verify_transaction_on_chain(invoice, txid)

                if tx_info:
                    verification_source = f"Blockchain ({invoice['crypto_network']})"
                    # Adapt blockchain explorer format to match MEXC format
                    tx_info['currency'] = invoice['crypto_currency']
                    tx_info['network'] = invoice['crypto_network']
                    tx_info['address'] = invoice['deposit_address']
                    tx_info['raw_data'] = tx_info  # Store full details

            if not tx_info:
                return {
                    "success": False,
                    "error": "Transaction not found on MEXC or blockchain explorers"
                }

            # Check if amount matches
            expected_amount = invoice['crypto_amount']
            tolerance = invoice.get('payment_tolerance', 0.005)
            received_amount = tx_info['amount']

            min_amount = expected_amount * (1 - tolerance)
            max_amount = expected_amount * (1 + tolerance)

            if not (min_amount <= received_amount <= max_amount):
                return {
                    "success": False,
                    "error": f"Amount mismatch: expected {expected_amount}, received {received_amount}"
                }

            # Check if address matches
            if tx_info.get('address') != invoice['deposit_address']:
                return {
                    "success": False,
                    "error": "Deposit address mismatch"
                }

            # Record payment as manually verified
            payment_data = {
                "invoice_id": invoice_id,
                "transaction_hash": txid,
                "amount_received": received_amount,
                "currency": tx_info['currency'],
                "network": tx_info['network'],
                "deposit_address": tx_info['address'],
                "status": PaymentStatus.CONFIRMED.value,
                "confirmations": tx_info.get('confirmations', 999),
                "required_confirmations": 1,  # Manual verification bypasses confirmation requirement
                "is_manual_verification": True,
                "verified_by": verified_by,
                "mexc_transaction_id": txid,
                "raw_api_response": tx_info.get('raw_data')
            }

            payment_id = self.db.create_payment_transaction(payment_data)

            # Mark invoice as paid
            self.db.update_invoice_status(
                invoice_id=invoice_id,
                status=InvoiceStatus.PAID.value,
                paid_at=datetime.now()
            )

            self.logger.info(
                f"✅ Manual verification successful for invoice {invoice['invoice_number']} "
                f"via {verification_source}"
            )

            return {
                "success": True,
                "payment_id": payment_id,
                "verification_source": verification_source,
                "message": f"Payment manually verified via {verification_source} and invoice marked as paid"
            }

        except Exception as e:
            self.logger.error(f"Manual verification failed: {e}")
            return {"success": False, "error": str(e)}

    def get_statistics(self) -> Dict[str, Any]:
        """Get polling service statistics"""
        return {
            **self.stats,
            "is_running": self.is_running,
            "poll_interval": self.poll_interval,
            "uptime": (datetime.now() - self.stats.get("start_time", datetime.now())).total_seconds()
            if self.stats.get("start_time") else 0
        }

    def check_overdue_invoices(self):
        """Check for overdue invoices and update their status"""
        conn = self.db.get_connection()
        cursor = conn.cursor()

        # Get configuration for overdue threshold
        overdue_days = int(self.db.get_config('invoice_overdue_days') or 7)

        # Find invoices that are past due date and not paid
        cursor.execute("""
            UPDATE invoices
            SET status = 'overdue', updated_at = CURRENT_TIMESTAMP
            WHERE status IN ('sent', 'partially_paid')
            AND date(due_date) < date('now', ? || ' days')
        """, (f"-{overdue_days}",))

        updated_count = cursor.rowcount
        conn.commit()
        conn.close()

        if updated_count > 0:
            self.logger.warning(f"Marked {updated_count} invoices as overdue")

        return updated_count
