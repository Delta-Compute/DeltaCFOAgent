#!/usr/bin/env python3
"""
Email Service for Crypto Invoice System
Handles email notifications using SMTP (Gmail or custom)
"""

import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any, Optional, List
from datetime import datetime
import os


logger = logging.getLogger(__name__)


class EmailService:
    """
    Email service supporting Gmail and custom SMTP configurations
    Sends notifications to company users about invoice events
    """

    # Default Gmail SMTP configuration
    DEFAULT_SMTP_HOST = 'smtp.gmail.com'
    DEFAULT_SMTP_PORT = 587
    DEFAULT_USE_TLS = True

    def __init__(self, db_manager):
        """
        Initialize email service

        Args:
            db_manager: Database manager for accessing user settings and logging
        """
        self.db_manager = db_manager

        # Load default credentials from environment (optional)
        self.default_smtp_username = os.getenv('SMTP_USERNAME')
        self.default_smtp_password = os.getenv('SMTP_PASSWORD')
        self.default_from_email = os.getenv('SMTP_FROM_EMAIL', 'invoices@deltacfo.com')
        self.default_from_name = os.getenv('SMTP_FROM_NAME', 'Delta CFO Invoices')

        logger.info("Email service initialized")

    def get_smtp_config(self, user_id: int) -> Dict[str, Any]:
        """
        Get SMTP configuration for user
        Falls back to default Gmail settings if user hasn't configured custom SMTP

        Args:
            user_id: User ID

        Returns:
            Dict with SMTP configuration
        """
        user = self.db_manager.get_user(user_id)

        if not user:
            raise ValueError(f"User {user_id} not found")

        # Check if user has custom SMTP configuration
        has_custom_smtp = (
            user.get('smtp_username') and
            user.get('smtp_password')
        )

        if has_custom_smtp:
            return {
                'host': user.get('smtp_host', self.DEFAULT_SMTP_HOST),
                'port': user.get('smtp_port', self.DEFAULT_SMTP_PORT),
                'username': user['smtp_username'],
                'password': user['smtp_password'],
                'from_email': user.get('smtp_from_email', user['email']),
                'from_name': user.get('smtp_from_name', user['company_name']),
                'use_tls': True
            }
        else:
            # Use default Gmail configuration
            return {
                'host': self.DEFAULT_SMTP_HOST,
                'port': self.DEFAULT_SMTP_PORT,
                'username': self.default_smtp_username,
                'password': self.default_smtp_password,
                'from_email': self.default_from_email,
                'from_name': self.default_from_name,
                'use_tls': self.DEFAULT_USE_TLS
            }

    def should_send_notification(self, user_id: int, notification_type: str) -> tuple[bool, Optional[str]]:
        """
        Check if notification should be sent for user

        Args:
            user_id: User ID
            notification_type: Type of notification

        Returns:
            Tuple of (should_send: bool, email_override: Optional[str])
        """
        preferences = self.db_manager.get_email_preferences(user_id)

        for pref in preferences:
            if pref['notification_type'] == notification_type:
                enabled = pref.get('enabled', True)
                email_override = pref.get('email_override')
                return enabled, email_override

        # Default to enabled if preference not found
        return True, None

    def send_email(
        self,
        user_id: int,
        recipient_email: str,
        subject: str,
        html_body: str,
        text_body: Optional[str] = None,
        notification_type: Optional[str] = None,
        invoice_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Send email via SMTP

        Args:
            user_id: User ID (for SMTP config)
            recipient_email: Recipient email address
            subject: Email subject
            html_body: HTML email body
            text_body: Plain text email body (optional, will strip HTML if not provided)
            notification_type: Type of notification (for logging)
            invoice_id: Related invoice ID (for logging)

        Returns:
            Dict with success status and message
        """
        try:
            # Get SMTP configuration
            smtp_config = self.get_smtp_config(user_id)

            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = f"{smtp_config['from_name']} <{smtp_config['from_email']}>"
            msg['To'] = recipient_email

            # Add text part (fallback)
            if text_body:
                text_part = MIMEText(text_body, 'plain')
                msg.attach(text_part)

            # Add HTML part
            html_part = MIMEText(html_body, 'html')
            msg.attach(html_part)

            # Send via SMTP
            logger.info(f"Sending email to {recipient_email} via {smtp_config['host']}")

            with smtplib.SMTP(smtp_config['host'], smtp_config['port']) as server:
                if smtp_config.get('use_tls', True):
                    server.starttls()

                # Login if credentials provided
                if smtp_config['username'] and smtp_config['password']:
                    server.login(smtp_config['username'], smtp_config['password'])

                server.send_message(msg)

            logger.info(f"Email sent successfully to {recipient_email}")

            # Log to database
            if notification_type:
                self.db_manager.log_email_sent(
                    user_id=user_id,
                    invoice_id=invoice_id,
                    notification_type=notification_type,
                    recipient_email=recipient_email,
                    subject=subject,
                    status='sent'
                )

            return {
                'success': True,
                'message': 'Email sent successfully'
            }

        except smtplib.SMTPAuthenticationError as e:
            error_msg = f"SMTP authentication failed: {str(e)}"
            logger.error(error_msg)

            # Log failure
            if notification_type:
                self.db_manager.log_email_sent(
                    user_id=user_id,
                    invoice_id=invoice_id,
                    notification_type=notification_type,
                    recipient_email=recipient_email,
                    subject=subject,
                    status='failed',
                    error_message=error_msg
                )

            return {
                'success': False,
                'error': 'SMTP authentication failed. Please check your email credentials.'
            }

        except smtplib.SMTPException as e:
            error_msg = f"SMTP error: {str(e)}"
            logger.error(error_msg)

            # Log failure
            if notification_type:
                self.db_manager.log_email_sent(
                    user_id=user_id,
                    invoice_id=invoice_id,
                    notification_type=notification_type,
                    recipient_email=recipient_email,
                    subject=subject,
                    status='failed',
                    error_message=error_msg
                )

            return {
                'success': False,
                'error': f'Failed to send email: {str(e)}'
            }

        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            logger.error(error_msg, exc_info=True)

            # Log failure
            if notification_type:
                self.db_manager.log_email_sent(
                    user_id=user_id,
                    invoice_id=invoice_id,
                    notification_type=notification_type,
                    recipient_email=recipient_email,
                    subject=subject,
                    status='failed',
                    error_message=error_msg
                )

            return {
                'success': False,
                'error': f'Failed to send email: {str(e)}'
            }

    def send_notification(
        self,
        user_id: int,
        notification_type: str,
        subject: str,
        html_body: str,
        text_body: Optional[str] = None,
        invoice_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Send notification email with preference checking

        Args:
            user_id: User ID
            notification_type: Type of notification
            subject: Email subject
            html_body: HTML email body
            text_body: Plain text email body (optional)
            invoice_id: Related invoice ID (optional)

        Returns:
            Dict with success status and message
        """
        # Check if notification is enabled
        should_send, email_override = self.should_send_notification(user_id, notification_type)

        if not should_send:
            logger.info(f"Notification '{notification_type}' disabled for user {user_id}")
            return {
                'success': True,
                'message': 'Notification disabled by user preference',
                'skipped': True
            }

        # Get user email
        user = self.db_manager.get_user(user_id)
        if not user:
            return {
                'success': False,
                'error': f'User {user_id} not found'
            }

        # Use email override if specified, otherwise use user's email
        recipient_email = email_override or user['email']

        # Send email
        return self.send_email(
            user_id=user_id,
            recipient_email=recipient_email,
            subject=subject,
            html_body=html_body,
            text_body=text_body,
            notification_type=notification_type,
            invoice_id=invoice_id
        )

    def send_bulk_notifications(
        self,
        notifications: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Send multiple notifications (for batch processing)

        Args:
            notifications: List of notification dicts with keys:
                - user_id
                - notification_type
                - subject
                - html_body
                - text_body (optional)
                - invoice_id (optional)

        Returns:
            Dict with success/failure counts
        """
        results = {
            'total': len(notifications),
            'sent': 0,
            'skipped': 0,
            'failed': 0,
            'errors': []
        }

        for notif in notifications:
            result = self.send_notification(
                user_id=notif['user_id'],
                notification_type=notif['notification_type'],
                subject=notif['subject'],
                html_body=notif['html_body'],
                text_body=notif.get('text_body'),
                invoice_id=notif.get('invoice_id')
            )

            if result.get('success'):
                if result.get('skipped'):
                    results['skipped'] += 1
                else:
                    results['sent'] += 1
            else:
                results['failed'] += 1
                results['errors'].append({
                    'user_id': notif['user_id'],
                    'notification_type': notif['notification_type'],
                    'error': result.get('error')
                })

        return results

    def test_smtp_connection(self, user_id: int) -> Dict[str, Any]:
        """
        Test SMTP connection for user

        Args:
            user_id: User ID

        Returns:
            Dict with success status and message
        """
        try:
            smtp_config = self.get_smtp_config(user_id)

            logger.info(f"Testing SMTP connection to {smtp_config['host']}:{smtp_config['port']}")

            with smtplib.SMTP(smtp_config['host'], smtp_config['port'], timeout=10) as server:
                if smtp_config.get('use_tls', True):
                    server.starttls()

                if smtp_config['username'] and smtp_config['password']:
                    server.login(smtp_config['username'], smtp_config['password'])

                logger.info("SMTP connection test successful")

                return {
                    'success': True,
                    'message': 'SMTP connection successful',
                    'config': {
                        'host': smtp_config['host'],
                        'port': smtp_config['port'],
                        'username': smtp_config['username'],
                        'from_email': smtp_config['from_email']
                    }
                }

        except smtplib.SMTPAuthenticationError as e:
            return {
                'success': False,
                'error': 'SMTP authentication failed. Please check your credentials.'
            }

        except Exception as e:
            return {
                'success': False,
                'error': f'Connection failed: {str(e)}'
            }
