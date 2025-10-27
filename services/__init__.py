"""
Services Module

Provides email and other service integrations.
"""

from .email_service import (
    EmailService,
    email_service,
    send_invitation_email,
    send_welcome_email,
    send_admin_transfer_notification
)

__all__ = [
    'EmailService',
    'email_service',
    'send_invitation_email',
    'send_welcome_email',
    'send_admin_transfer_notification'
]
