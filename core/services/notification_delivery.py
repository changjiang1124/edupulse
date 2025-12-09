"""
Shared delivery helpers for email and SMS notifications.
These helpers encapsulate sender resolution and formatting so they can be reused
by both synchronous code paths and queued tasks.
"""
import logging
from typing import Optional
from django.conf import settings
from django.core.mail import EmailMessage, get_connection
from core.models import OrganisationSettings, EmailSettings
from core.sms_backends import send_sms

logger = logging.getLogger(__name__)


def send_email_notification(
    recipient_email: str,
    recipient_name: str,
    subject: str,
    message: str,
    message_type: str,
    recipient_type: str,
) -> bool:
    """Send a single email notification with sane defaults."""
    try:
        org_settings = OrganisationSettings.get_instance()
        organisation_name = org_settings.organisation_name or 'Perth Art School'

        email_config = EmailSettings.get_active_config()
        reply_to_email: Optional[str] = org_settings.reply_to_email
        sender_name: Optional[str] = organisation_name
        sender_address: Optional[str] = None

        if email_config:
            sender_name = email_config.from_name or organisation_name
            sender_address = email_config.from_email
            reply_to_email = email_config.reply_to_email or reply_to_email
        else:
            sender_name = getattr(settings, 'DEFAULT_FROM_NAME', organisation_name)
            sender_address = (
                getattr(settings, 'DEFAULT_FROM_EMAIL', None)
                or getattr(settings, 'EMAIL_HOST_USER', None)
                or org_settings.contact_email
            )

        if not sender_address:
            raise ValueError('Email sender address is not configured')

        formatted_from = f'{sender_name} <{sender_address}>' if sender_name else sender_address

        email = EmailMessage(
            subject=subject,
            body=f"Dear {recipient_name},\n\n{message}\n\nBest regards,\n{organisation_name}",
            from_email=formatted_from,
            to=[recipient_email],
            reply_to=[reply_to_email] if reply_to_email else None,
            connection=get_connection(),
        )

        email.send()
        logger.info("Email notification sent to %s (%s)", recipient_email, message_type)
        return True

    except Exception as exc:
        logger.error("Failed to send email notification to %s: %s", recipient_email, exc)
        return False


def send_sms_notification(
    recipient_phone: str,
    recipient_name: str,
    message: str,
    message_type: str,
    recipient_type: str,
) -> bool:
    """Send a single SMS notification with truncation and logging."""
    try:
        org_settings = OrganisationSettings.get_instance()
        organisation_name = org_settings.organisation_name or 'Perth Art School'

        sms_message = f"Hi {recipient_name}, {message} - {organisation_name}"
        if len(sms_message) > 160:
            sms_message = sms_message[:157] + "..."

        success = send_sms(recipient_phone, sms_message, message_type)
        if success:
            logger.info("SMS notification sent to %s (%s)", recipient_phone, message_type)
            return True

        logger.error("SMS notification failed to %s (%s)", recipient_phone, message_type)
        return False

    except Exception as exc:
        logger.error("Error sending SMS notification to %s: %s", recipient_phone, exc)
        return False
