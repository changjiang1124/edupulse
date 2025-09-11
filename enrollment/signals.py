"""
Django signals for automatic enrollment-class attendance management

This module handles automatic creation of attendance records when:
1. A student enrollment is confirmed for a course
2. A new class is created for a course with existing enrollments
"""
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.db import transaction
from .models import Enrollment, Attendance
from academics.models import Class
from .services import EnrollmentAttendanceService, ClassAttendanceService
import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Enrollment)
def create_attendance_for_confirmed_enrollment(sender, instance, created, **kwargs):
    """
    When an enrollment is confirmed, automatically create attendance records
    for all existing active classes of that course
    """
    # Only process confirmed enrollments
    if instance.status != 'confirmed':
        return
    
    # Check if this is a status change to confirmed (not a new confirmed enrollment)
    if not created and hasattr(instance, '_original_status'):
        if instance._original_status != 'confirmed':
            # This is an enrollment being updated to confirmed status
            result = EnrollmentAttendanceService.auto_create_attendance_for_enrollment(instance)
            logger.info(f"Enrollment confirmation signal: {result['message']}")
    elif created and instance.status == 'confirmed':
        # This is a new enrollment created as confirmed
        result = EnrollmentAttendanceService.auto_create_attendance_for_enrollment(instance)
        logger.info(f"New confirmed enrollment signal: {result['message']}")


@receiver(pre_save, sender=Enrollment)
def track_enrollment_status_change(sender, instance, **kwargs):
    """Track the original status before save to detect status changes"""
    if instance.pk:
        try:
            original = Enrollment.objects.get(pk=instance.pk)
            instance._original_status = original.status
        except Enrollment.DoesNotExist:
            instance._original_status = None
    else:
        instance._original_status = None


@receiver(post_save, sender=Class)
def create_attendance_for_new_class(sender, instance, created, **kwargs):
    """
    When a new class is created, automatically create attendance records
    for all confirmed enrollments of that course
    """
    # Only process newly created active classes
    if not created or not instance.is_active:
        return
    
    result = ClassAttendanceService.auto_create_attendance_for_class(instance)
    logger.info(f"New class creation signal: {result['message']}")


# Legacy helper functions for backward compatibility
def _create_attendance_records_for_enrollment(enrollment, classes):
    """Legacy helper - use EnrollmentAttendanceService instead"""
    return EnrollmentAttendanceService.auto_create_attendance_for_enrollment(enrollment)


def _create_attendance_records_for_class(class_instance, enrollments):
    """Legacy helper - use ClassAttendanceService instead"""
    return ClassAttendanceService.auto_create_attendance_for_class(class_instance)


def sync_all_attendance_records():
    """
    Utility function to sync all attendance records for existing data
    This can be called from a management command
    """
    from .services import AttendanceSyncService
    result = AttendanceSyncService.sync_all_attendance()
    logger.info(f"Manual sync completed: {result['message']}")
    return result.get('total_created', 0)