"""
Test Email Service

Test script to verify SendGrid/SMTP email sending functionality.
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

from services.email_service import EmailService

def test_email_service():
    """Test email service configuration and basic sending."""

    print("=== Email Service Test ===\n")

    # Initialize email service
    email_service = EmailService()

    print(f"Provider: {email_service.provider}")
    print(f"From Email: {email_service.from_email}")
    print(f"From Name: {email_service.from_name}")
    print(f"App Base URL: {email_service.app_base_url}")

    if email_service.provider == 'sendgrid':
        if email_service.sendgrid_api_key and email_service.sendgrid_api_key != 'your_sendgrid_api_key_here':
            print(f"SendGrid API Key: {'*' * 20} (configured)")
        else:
            print("SendGrid API Key: NOT CONFIGURED")
            print("\nTo configure SendGrid:")
            print("1. Sign up at https://sendgrid.com/")
            print("2. Create an API key in Settings > API Keys")
            print("3. Add to .env: SENDGRID_API_KEY=your_actual_api_key")
            return False

    elif email_service.provider == 'smtp':
        if email_service.smtp_username and email_service.smtp_password:
            print(f"SMTP Host: {email_service.smtp_host}:{email_service.smtp_port}")
            print(f"SMTP Username: {email_service.smtp_username}")
            print(f"SMTP TLS: {email_service.smtp_use_tls}")
        else:
            print("SMTP Credentials: NOT CONFIGURED")
            print("\nTo configure SMTP:")
            print("1. For Gmail: Enable 2FA and create app password")
            print("2. Add to .env:")
            print("   SMTP_USERNAME=your_email@gmail.com")
            print("   SMTP_PASSWORD=your_app_password")
            return False

    print("\n=== Testing Welcome Email ===\n")

    # Test data
    test_email = os.getenv('TEST_EMAIL', 'test@example.com')

    if test_email == 'test@example.com':
        print("WARNING: Using default test email (test@example.com)")
        print("Set TEST_EMAIL environment variable to use your email")
        print("\nSkipping actual email send to avoid failures.")
        return True

    print(f"Sending welcome email to: {test_email}")

    # Try to send welcome email
    success = email_service.send_welcome_email(
        to_email=test_email,
        user_name="Test User",
        company_name="Delta CFO Agent Test"
    )

    if success:
        print("SUCCESS: Welcome email sent!")
        print("Check your inbox (and spam folder)")
    else:
        print("FAILED: Could not send email")
        print("Check logs for detailed error messages")

    return success


def test_invitation_email():
    """Test invitation email sending."""

    print("\n=== Testing Invitation Email ===\n")

    email_service = EmailService()
    test_email = os.getenv('TEST_EMAIL', 'test@example.com')

    if test_email == 'test@example.com':
        print("Skipping invitation email test (no TEST_EMAIL configured)")
        return True

    print(f"Sending invitation email to: {test_email}")

    success = email_service.send_invitation_email(
        to_email=test_email,
        invitation_token="test_token_123456",
        inviter_name="John Doe",
        company_name="Delta Test Company",
        role="employee",
        expires_in_days=7
    )

    if success:
        print("SUCCESS: Invitation email sent!")
    else:
        print("FAILED: Could not send invitation email")

    return success


if __name__ == "__main__":
    print("Starting Email Service Tests\n")
    print("=" * 50)

    # Test basic configuration
    config_ok = test_email_service()

    if not config_ok:
        print("\n" + "=" * 50)
        print("Email service not fully configured.")
        print("Please configure SendGrid or SMTP in .env file")
        sys.exit(1)

    # Test invitation email
    test_invitation_email()

    print("\n" + "=" * 50)
    print("Email service tests completed!")
