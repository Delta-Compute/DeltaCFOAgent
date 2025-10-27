"""
Email Service

Provides email sending functionality using SendGrid for user invitations,
notifications, and transactional emails.
"""

import os
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

try:
    from sendgrid import SendGridAPIClient
    from sendgrid.helpers.mail import Mail, Email, To, Content
    SENDGRID_AVAILABLE = True
except ImportError:
    SENDGRID_AVAILABLE = False
    logging.warning("SendGrid not available. Install with: pip install sendgrid")

logger = logging.getLogger(__name__)


class EmailService:
    """Email service for sending transactional and notification emails."""

    def __init__(self):
        """Initialize email service with configuration from environment."""
        self.provider = os.getenv('EMAIL_PROVIDER', 'sendgrid').lower()
        self.from_email = os.getenv('SENDGRID_FROM_EMAIL', 'noreply@deltacfo.com')
        self.from_name = os.getenv('SENDGRID_FROM_NAME', 'Delta CFO Agent')
        self.app_base_url = os.getenv('APP_BASE_URL', 'http://localhost:5001')

        # SendGrid configuration
        self.sendgrid_api_key = os.getenv('SENDGRID_API_KEY')

        # SMTP configuration (fallback)
        self.smtp_host = os.getenv('SMTP_HOST', 'smtp.gmail.com')
        self.smtp_port = int(os.getenv('SMTP_PORT', '587'))
        self.smtp_username = os.getenv('SMTP_USERNAME')
        self.smtp_password = os.getenv('SMTP_PASSWORD')
        self.smtp_use_tls = os.getenv('SMTP_USE_TLS', 'true').lower() == 'true'

        # Validate configuration
        if self.provider == 'sendgrid' and not self.sendgrid_api_key:
            logger.warning("SendGrid API key not configured. Email sending will fail.")

        if self.provider == 'smtp' and (not self.smtp_username or not self.smtp_password):
            logger.warning("SMTP credentials not configured. Email sending will fail.")

    def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        plain_text_content: Optional[str] = None,
        to_name: Optional[str] = None
    ) -> bool:
        """
        Send an email using the configured provider.

        Args:
            to_email: Recipient email address
            subject: Email subject
            html_content: HTML email content
            plain_text_content: Plain text version (optional)
            to_name: Recipient name (optional)

        Returns:
            True if email sent successfully, False otherwise
        """
        try:
            if self.provider == 'sendgrid':
                return self._send_via_sendgrid(
                    to_email, subject, html_content, plain_text_content, to_name
                )
            elif self.provider == 'smtp':
                return self._send_via_smtp(
                    to_email, subject, html_content, plain_text_content, to_name
                )
            else:
                logger.error(f"Unknown email provider: {self.provider}")
                return False

        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {e}")
            return False

    def _send_via_sendgrid(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        plain_text_content: Optional[str],
        to_name: Optional[str]
    ) -> bool:
        """Send email via SendGrid API."""
        if not SENDGRID_AVAILABLE:
            logger.error("SendGrid library not installed")
            return False

        if not self.sendgrid_api_key:
            logger.error("SendGrid API key not configured")
            return False

        try:
            message = Mail(
                from_email=Email(self.from_email, self.from_name),
                to_emails=To(to_email, to_name),
                subject=subject,
                html_content=Content("text/html", html_content)
            )

            if plain_text_content:
                message.add_content(Content("text/plain", plain_text_content))

            sg = SendGridAPIClient(self.sendgrid_api_key)
            response = sg.send(message)

            if response.status_code in [200, 201, 202]:
                logger.info(f"Email sent successfully to {to_email}")
                return True
            else:
                logger.error(f"SendGrid returned status {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"SendGrid error: {e}")
            return False

    def _send_via_smtp(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        plain_text_content: Optional[str],
        to_name: Optional[str]
    ) -> bool:
        """Send email via SMTP."""
        try:
            msg = MIMEMultipart('alternative')
            msg['From'] = f"{self.from_name} <{self.from_email}>"
            msg['To'] = f"{to_name} <{to_email}>" if to_name else to_email
            msg['Subject'] = subject

            # Add plain text part
            if plain_text_content:
                part1 = MIMEText(plain_text_content, 'plain')
                msg.attach(part1)

            # Add HTML part
            part2 = MIMEText(html_content, 'html')
            msg.attach(part2)

            # Send email
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                if self.smtp_use_tls:
                    server.starttls()

                server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)

            logger.info(f"Email sent successfully via SMTP to {to_email}")
            return True

        except Exception as e:
            logger.error(f"SMTP error: {e}")
            return False

    def send_invitation_email(
        self,
        to_email: str,
        invitation_token: str,
        inviter_name: str,
        company_name: str,
        role: str,
        expires_in_days: int = 7
    ) -> bool:
        """
        Send invitation email to a new user.

        Args:
            to_email: Recipient email address
            invitation_token: Unique invitation token
            inviter_name: Name of person who sent invitation
            company_name: Company/tenant name
            role: User role (e.g., 'employee', 'cfo_assistant')
            expires_in_days: Days until invitation expires

        Returns:
            True if email sent successfully, False otherwise
        """
        invitation_url = f"{self.app_base_url}/auth/accept-invitation?token={invitation_token}"
        expiry_date = (datetime.now() + timedelta(days=expires_in_days)).strftime('%B %d, %Y')

        # Format role for display
        role_display = role.replace('_', ' ').title()

        subject = f"You've been invited to join {company_name} on Delta CFO Agent"

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Invitation to Delta CFO Agent</title>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #2563eb; color: white; padding: 30px; text-align: center; border-radius: 8px 8px 0 0; }}
                .content {{ background-color: #ffffff; padding: 30px; border: 1px solid #e5e7eb; border-top: none; }}
                .button {{ display: inline-block; padding: 12px 30px; background-color: #2563eb; color: white; text-decoration: none; border-radius: 6px; margin: 20px 0; }}
                .footer {{ text-align: center; padding: 20px; color: #6b7280; font-size: 14px; }}
                .info-box {{ background-color: #f3f4f6; padding: 15px; border-radius: 6px; margin: 20px 0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>You're Invited!</h1>
                </div>
                <div class="content">
                    <p>Hello,</p>
                    <p><strong>{inviter_name}</strong> has invited you to join <strong>{company_name}</strong> on Delta CFO Agent.</p>

                    <div class="info-box">
                        <p><strong>Your Role:</strong> {role_display}</p>
                        <p><strong>Company:</strong> {company_name}</p>
                        <p><strong>Expires:</strong> {expiry_date}</p>
                    </div>

                    <p>Click the button below to accept your invitation and create your account:</p>

                    <center>
                        <a href="{invitation_url}" class="button">Accept Invitation</a>
                    </center>

                    <p style="color: #6b7280; font-size: 14px; margin-top: 20px;">
                        If the button doesn't work, copy and paste this link into your browser:<br>
                        <a href="{invitation_url}">{invitation_url}</a>
                    </p>

                    <p style="color: #ef4444; font-size: 14px; margin-top: 20px;">
                        This invitation will expire on {expiry_date}. If you didn't expect this invitation, you can safely ignore this email.
                    </p>
                </div>
                <div class="footer">
                    <p>&copy; 2025 Delta CFO Agent. All rights reserved.</p>
                    <p>Powered by AI-driven financial intelligence.</p>
                </div>
            </div>
        </body>
        </html>
        """

        plain_text = f"""
        You've been invited to join {company_name} on Delta CFO Agent

        {inviter_name} has invited you to join as a {role_display}.

        Your Role: {role_display}
        Company: {company_name}
        Expires: {expiry_date}

        Accept your invitation by visiting this link:
        {invitation_url}

        This invitation will expire on {expiry_date}.
        If you didn't expect this invitation, you can safely ignore this email.

        - Delta CFO Agent Team
        """

        return self.send_email(
            to_email=to_email,
            subject=subject,
            html_content=html_content,
            plain_text_content=plain_text
        )

    def send_welcome_email(
        self,
        to_email: str,
        user_name: str,
        company_name: str
    ) -> bool:
        """
        Send welcome email to a new user.

        Args:
            to_email: Recipient email address
            user_name: User's display name
            company_name: Company/tenant name

        Returns:
            True if email sent successfully, False otherwise
        """
        subject = f"Welcome to Delta CFO Agent - {company_name}"

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Welcome to Delta CFO Agent</title>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #2563eb; color: white; padding: 30px; text-align: center; border-radius: 8px 8px 0 0; }}
                .content {{ background-color: #ffffff; padding: 30px; border: 1px solid #e5e7eb; border-top: none; }}
                .button {{ display: inline-block; padding: 12px 30px; background-color: #2563eb; color: white; text-decoration: none; border-radius: 6px; margin: 20px 0; }}
                .footer {{ text-align: center; padding: 20px; color: #6b7280; font-size: 14px; }}
                .features {{ background-color: #f3f4f6; padding: 20px; border-radius: 6px; margin: 20px 0; }}
                .feature {{ margin: 10px 0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Welcome to Delta CFO Agent!</h1>
                </div>
                <div class="content">
                    <p>Hi {user_name},</p>
                    <p>Welcome to <strong>{company_name}</strong> on Delta CFO Agent! We're excited to have you on board.</p>

                    <div class="features">
                        <h3>What you can do:</h3>
                        <div class="feature">✓ Track and manage transactions</div>
                        <div class="feature">✓ Process invoices automatically</div>
                        <div class="feature">✓ Generate financial reports</div>
                        <div class="feature">✓ Collaborate with your team</div>
                        <div class="feature">✓ Access AI-powered insights</div>
                    </div>

                    <p>Get started by logging in to your account:</p>

                    <center>
                        <a href="{self.app_base_url}/login" class="button">Go to Dashboard</a>
                    </center>

                    <p>If you have any questions, feel free to reach out to your team administrator or contact support.</p>
                </div>
                <div class="footer">
                    <p>&copy; 2025 Delta CFO Agent. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """

        plain_text = f"""
        Welcome to Delta CFO Agent!

        Hi {user_name},

        Welcome to {company_name} on Delta CFO Agent! We're excited to have you on board.

        What you can do:
        - Track and manage transactions
        - Process invoices automatically
        - Generate financial reports
        - Collaborate with your team
        - Access AI-powered insights

        Get started by logging in: {self.app_base_url}/login

        If you have any questions, feel free to reach out to your team administrator.

        - Delta CFO Agent Team
        """

        return self.send_email(
            to_email=to_email,
            subject=subject,
            html_content=html_content,
            plain_text_content=plain_text,
            to_name=user_name
        )

    def send_admin_transfer_notification(
        self,
        to_email: str,
        new_admin_name: str,
        company_name: str,
        transferred_by_name: str
    ) -> bool:
        """
        Send notification when admin role is transferred.

        Args:
            to_email: New admin's email
            new_admin_name: New admin's name
            company_name: Company name
            transferred_by_name: Name of person who transferred the role

        Returns:
            True if email sent successfully, False otherwise
        """
        subject = f"You are now an Administrator for {company_name}"

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #2563eb; color: white; padding: 30px; text-align: center; }}
                .content {{ background-color: #ffffff; padding: 30px; border: 1px solid #e5e7eb; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Admin Role Transferred</h1>
                </div>
                <div class="content">
                    <p>Hi {new_admin_name},</p>
                    <p>{transferred_by_name} has transferred administrator rights for <strong>{company_name}</strong> to you.</p>
                    <p>You now have full administrative access to manage users, settings, and billing.</p>
                    <p>Login to your account to get started: <a href="{self.app_base_url}/login">Go to Dashboard</a></p>
                </div>
            </div>
        </body>
        </html>
        """

        return self.send_email(
            to_email=to_email,
            subject=subject,
            html_content=html_content,
            to_name=new_admin_name
        )


# Global email service instance
email_service = EmailService()


def send_invitation_email(*args, **kwargs) -> bool:
    """Convenience function to send invitation email."""
    return email_service.send_invitation_email(*args, **kwargs)


def send_welcome_email(*args, **kwargs) -> bool:
    """Convenience function to send welcome email."""
    return email_service.send_welcome_email(*args, **kwargs)


def send_admin_transfer_notification(*args, **kwargs) -> bool:
    """Convenience function to send admin transfer notification."""
    return email_service.send_admin_transfer_notification(*args, **kwargs)
