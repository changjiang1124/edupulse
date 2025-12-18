"""
Helper functions to enqueue notification jobs with django-rq.
Provides graceful fallback to synchronous sending when Redis/queue
is unavailable so user actions are not blocked.
"""
import logging
from typing import Dict, Optional
import django_rq
from core.services.notification_delivery import (
    send_email_notification,
    send_sms_notification,
)

logger = logging.getLogger(__name__)

QUEUE_NAME = 'notifications'


def _get_queue():
    return django_rq.get_queue(QUEUE_NAME)


def enqueue_email_notification(payload: Dict) -> Dict:
    """
    Enqueue an email notification. Payload keys:
    recipient_email, recipient_name, subject, message, message_type, recipient_type
    """
    try:
        queue = _get_queue()
        job = queue.enqueue('core.tasks.send_email_notification_task', **payload)
        return {'queued': True, 'job_id': job.id}
    except Exception as exc:
        logger.warning("Queueing email failed, sending synchronously: %s", exc)
        sent = send_email_notification(**payload)
        if sent:
            _consume_quota('email', 1)
        return {'queued': False, 'sent': sent, 'error': str(exc)}


def enqueue_sms_notification(payload: Dict) -> Dict:
    """
    Enqueue an SMS notification. Payload keys:
    recipient_phone, recipient_name, message, message_type, recipient_type
    """
    try:
        queue = _get_queue()
        job = queue.enqueue('core.tasks.send_sms_notification_task', **payload)
        return {'queued': True, 'job_id': job.id}
    except Exception as exc:
        logger.warning("Queueing SMS failed, sending synchronously: %s", exc)
        sent = send_sms_notification(**payload)
        if sent:
            _consume_quota('sms', 1)
        return {'queued': False, 'sent': sent, 'error': str(exc)}


def enqueue_enrollment_pending_email(enrollment_id: int, recipient_email: Optional[str], fee_breakdown: Optional[Dict]) -> Dict:
    """Queue enrollment pending email; fall back to synchronous send if needed."""
    try:
        queue = _get_queue()
        job = queue.enqueue(
            'core.tasks.send_enrollment_pending_email_task',
            enrollment_id=enrollment_id,
            recipient_email=recipient_email,
            fee_breakdown=fee_breakdown,
        )
        return {'queued': True, 'job_id': job.id}
    except Exception as exc:
        logger.warning("Queueing enrollment pending email failed, sending synchronously: %s", exc)
        sent = _send_pending_email_sync(enrollment_id, recipient_email, fee_breakdown)
        return {'queued': False, 'sent': sent, 'error': str(exc)}


def enqueue_enrollment_welcome_email(enrollment_id: int) -> Dict:
    """Queue enrollment welcome/confirmation email; fall back to synchronous send."""
    try:
        queue = _get_queue()
        job = queue.enqueue('core.tasks.send_enrollment_welcome_email_task', enrollment_id=enrollment_id)
        return {'queued': True, 'job_id': job.id}
    except Exception as exc:
        logger.warning("Queueing enrollment welcome email failed, sending synchronously: %s", exc)
        sent = _send_welcome_email_sync(enrollment_id)
        return {'queued': False, 'sent': sent, 'error': str(exc)}


def _consume_quota(notification_type: str, count: int):
    from core.models import NotificationQuota
    NotificationQuota.consume_quota(notification_type, count)


def _send_pending_email_sync(enrollment_id: int, recipient_email: Optional[str], fee_breakdown: Optional[Dict]) -> bool:
    from enrollment.models import Enrollment
    from core.services.notification_service import NotificationService

    enrollment = Enrollment.objects.filter(pk=enrollment_id).first()
    if not enrollment:
        logger.error("Enrollment %s not found for pending email fallback", enrollment_id)
        return False
    return NotificationService.send_enrollment_pending_email(
        enrollment=enrollment,
        recipient_email=recipient_email,
        fee_breakdown=fee_breakdown,
    )


def _send_welcome_email_sync(enrollment_id: int) -> bool:
    from enrollment.models import Enrollment
    from core.services.notification_service import NotificationService

    enrollment = Enrollment.objects.filter(pk=enrollment_id).first()
    if not enrollment:
        logger.error("Enrollment %s not found for welcome email fallback", enrollment_id)
        return False
    return NotificationService.send_welcome_email(enrollment)


def enqueue_enrollment_confirmation_email(enrollment_id: int) -> Dict:
    """Queue enrollment confirmation email; fall back to synchronous send."""
    try:
        queue = _get_queue()
        job = queue.enqueue('core.tasks.send_enrollment_confirmation_email_task', enrollment_id=enrollment_id)
        return {'queued': True, 'job_id': job.id}
    except Exception as exc:
        logger.warning("Queueing enrollment confirmation email failed, sending synchronously: %s", exc)
        sent = _send_confirmation_email_sync(enrollment_id)
        return {'queued': False, 'sent': sent, 'error': str(exc)}


def _send_confirmation_email_sync(enrollment_id: int) -> bool:
    from enrollment.models import Enrollment
    from core.services.notification_service import NotificationService

    enrollment = Enrollment.objects.filter(pk=enrollment_id).first()
    if not enrollment:
        logger.error("Enrollment %s not found for confirmation email fallback", enrollment_id)
        return False
    return NotificationService.send_enrollment_confirmation(enrollment)


def enqueue_new_enrollment_admin_notification(enrollment_id: int) -> Dict:
    """Queue admin notification email for new enrollment; fall back to synchronous send."""
    try:
        queue = _get_queue()
        job = queue.enqueue('core.tasks.send_new_enrollment_admin_notification_task', enrollment_id=enrollment_id)
        return {'queued': True, 'job_id': job.id}
    except Exception as exc:
        logger.warning("Queueing admin notification failed, sending synchronously: %s", exc)
        sent = _send_admin_notification_sync(enrollment_id)
        return {'queued': False, 'sent': sent, 'error': str(exc)}


def _send_admin_notification_sync(enrollment_id: int) -> bool:
    from enrollment.models import Enrollment
    from core.services.notification_service import NotificationService

    enrollment = Enrollment.objects.filter(pk=enrollment_id).first()
    if not enrollment:
        logger.error("Enrollment %s not found for admin notification fallback", enrollment_id)
        return False
    return NotificationService.send_new_enrollment_admin_notification(enrollment)
