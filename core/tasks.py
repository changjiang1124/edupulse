"""
django-rq task definitions for notifications.
These tasks are queued by core.services.notification_queue and are safe to run
in background workers.
"""
import logging
from django.utils import timezone
from core.models import NotificationQuota, EmailLog, SMSLog
from core.services.notification_delivery import (
    send_email_notification,
    send_sms_notification,
)
from core.services.notification_service import NotificationService

logger = logging.getLogger(__name__)

EMAIL_TYPE_CHOICES = {choice[0] for choice in EmailLog.TYPE_CHOICES}
SMS_TYPE_CHOICES = {choice[0] for choice in SMSLog.TYPE_CHOICES}


def send_email_notification_task(
    recipient_email: str,
    recipient_name: str,
    subject: str,
    message: str,
    message_type: str,
    recipient_type: str,
):
    """Background job: send a single email notification and update quota/logs."""
    email_type = message_type if message_type in EMAIL_TYPE_CHOICES else 'general'
    success = send_email_notification(
        recipient_email=recipient_email,
        recipient_name=recipient_name,
        subject=subject,
        message=message,
        message_type=email_type,
        recipient_type=recipient_type,
    )

    if success:
        NotificationQuota.consume_quota('email', 1)
        EmailLog.objects.create(
            recipient_email=recipient_email,
            recipient_type=recipient_type,
            subject=subject,
            content=message,
            email_type=email_type,
            status='sent',
            email_backend='django_rq',
            sent_at=timezone.now(),
        )
        return True

    EmailLog.objects.create(
        recipient_email=recipient_email,
        recipient_type=recipient_type,
        subject=subject,
        content=message,
        email_type=email_type,
        status='failed',
        error_message='Email send failed in task',
        email_backend='django_rq',
        sent_at=timezone.now(),
    )
    raise RuntimeError(f"Email notification failed for {recipient_email}")


def send_sms_notification_task(
    recipient_phone: str,
    recipient_name: str,
    message: str,
    message_type: str,
    recipient_type: str,
):
    """Background job: send a single SMS notification and update quota/logs."""
    sms_type = message_type if message_type in SMS_TYPE_CHOICES else 'general'
    success = send_sms_notification(
        recipient_phone=recipient_phone,
        recipient_name=recipient_name,
        message=message,
        message_type=sms_type,
        recipient_type=recipient_type,
    )

    if success:
        NotificationQuota.consume_quota('sms', 1)
        SMSLog.objects.create(
            recipient_phone=recipient_phone,
            recipient_type=recipient_type,
            content=message,
            sms_type=sms_type,
            status='sent',
            backend_type='django_rq',
            sent_at=timezone.now(),
        )
        return True

    SMSLog.objects.create(
        recipient_phone=recipient_phone,
        recipient_type=recipient_type,
        content=message,
        sms_type=sms_type,
        status='failed',
        error_message='SMS send failed in task',
        backend_type='django_rq',
        sent_at=timezone.now(),
    )
    raise RuntimeError(f"SMS notification failed for {recipient_phone}")


def send_enrollment_pending_email_task(enrollment_id: int, recipient_email=None, fee_breakdown=None):
    """Background job: send pending enrollment email (with invoice attachment)."""
    from enrollment.models import Enrollment

    enrollment = Enrollment.objects.filter(pk=enrollment_id).first()
    if not enrollment:
        logger.error("Enrollment %s not found for pending email task", enrollment_id)
        raise RuntimeError(f"Enrollment {enrollment_id} not found")

    sent = NotificationService.send_enrollment_pending_email(
        enrollment=enrollment,
        recipient_email=recipient_email,
        fee_breakdown=fee_breakdown,
    )
    if not sent:
        raise RuntimeError(f"Pending enrollment email failed for {enrollment_id}")
    return True


def send_enrollment_confirmation_email_task(enrollment_id: int):
    """Background job: send enrollment confirmation email (without welcome extras)."""
    from enrollment.models import Enrollment

    enrollment = Enrollment.objects.filter(pk=enrollment_id).first()
    if not enrollment:
        logger.error("Enrollment %s not found for confirmation email task", enrollment_id)
        raise RuntimeError(f"Enrollment {enrollment_id} not found")

    sent = NotificationService.send_enrollment_confirmation(enrollment)
    if not sent:
        raise RuntimeError(f"Confirmation email failed for {enrollment_id}")
    return True


def send_enrollment_welcome_email_task(enrollment_id: int):
    """Background job: send welcome/confirmation email for confirmed enrollments."""
    from enrollment.models import Enrollment

    enrollment = Enrollment.objects.filter(pk=enrollment_id).first()
    if not enrollment:
        logger.error("Enrollment %s not found for welcome email task", enrollment_id)
        raise RuntimeError(f"Enrollment {enrollment_id} not found")

    sent = NotificationService.send_welcome_email(enrollment)
    if not sent:
        raise RuntimeError(f"Welcome email failed for {enrollment_id}")
    return True


def send_new_enrollment_admin_notification_task(enrollment_id: int):
    """Background job: notify organisation admins about a new enrollment submission."""
    from enrollment.models import Enrollment

    enrollment = Enrollment.objects.filter(pk=enrollment_id).first()
    if not enrollment:
        logger.error("Enrollment %s not found for admin notification task", enrollment_id)
        raise RuntimeError(f"Enrollment {enrollment_id} not found")

    sent = NotificationService.send_new_enrollment_admin_notification(enrollment)
    if not sent:
        raise RuntimeError(f"Admin notification failed for {enrollment_id}")
    return True
