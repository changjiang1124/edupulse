"""
Service layer for enrollment and attendance automation

This module provides services for managing automatic attendance creation
and synchronization between enrollments, classes, and attendance records.
"""
from django.db import transaction
from django.utils import timezone
from django.db import models
from .models import Enrollment, Attendance
from academics.models import Class, Course
from students.models import Student
import logging

logger = logging.getLogger(__name__)


class EnrollmentAttendanceService:
    """Service for managing attendance automation related to enrollments"""

    @staticmethod
    def _is_class_within_window(enrollment, class_instance):
        class_datetime = class_instance.get_class_datetime()
        active_from = enrollment.active_from
        active_until = enrollment.active_until

        if active_from and timezone.is_naive(active_from):
            active_from = timezone.make_aware(active_from, timezone.get_current_timezone())
        if active_until and timezone.is_naive(active_until):
            active_until = timezone.make_aware(active_until, timezone.get_current_timezone())

        if active_from and class_datetime < active_from:
            return False
        if active_until and class_datetime >= active_until:
            return False
        return True
    
    @staticmethod
    def auto_create_attendance_for_enrollment(enrollment):
        """
        Create attendance records for a confirmed enrollment across all existing active classes
        
        Args:
            enrollment (Enrollment): The confirmed enrollment
            
        Returns:
            dict: Result with status, created_count, and message
        """
        if enrollment.status != 'confirmed':
            return {
                'status': 'skipped',
                'created_count': 0,
                'message': 'Enrollment is not confirmed'
            }
        
        # Get all active classes for this course
        active_classes = enrollment.course.classes.filter(is_active=True)
        eligible_classes = [
            class_instance
            for class_instance in active_classes
            if EnrollmentAttendanceService._is_class_within_window(enrollment, class_instance)
        ]
        
        if not eligible_classes:
            return {
                'status': 'success',
                'created_count': 0,
                'message': 'No eligible classes found for course'
            }
        
        created_count = 0
        errors = []
        
        try:
            with transaction.atomic():
                for class_instance in eligible_classes:
                    try:
                        attendance_record, created = Attendance.objects.get_or_create(
                            student=enrollment.student,
                            class_instance=class_instance,
                            defaults={
                                'status': 'unmarked',  # Default status
                                'attendance_time': class_instance.get_class_datetime()
                            }
                        )
                        
                        if created:
                            created_count += 1
                            logger.debug(
                                f"Created attendance record for {enrollment.student.get_full_name()} "
                                f"in class {class_instance} on {class_instance.date}"
                            )
                    
                    except Exception as e:
                        error_msg = f"Error creating attendance for class {class_instance.id}: {str(e)}"
                        errors.append(error_msg)
                        logger.error(error_msg)
            
            message = f"Created {created_count} attendance records"
            if errors:
                message += f" with {len(errors)} errors"
            
            logger.info(
                f"Auto-created {created_count} attendance records for enrollment "
                f"{enrollment.student.get_full_name()} in course {enrollment.course.name}"
            )
            
            return {
                'status': 'success',
                'created_count': created_count,
                'message': message,
                'errors': errors
            }
            
        except Exception as e:
            error_msg = f"Transaction failed while creating attendance records: {str(e)}"
            logger.error(error_msg)
            return {
                'status': 'error',
                'created_count': 0,
                'message': error_msg
            }
    
    @staticmethod
    def sync_enrollment_attendance(enrollment):
        """
        Synchronize attendance records for an enrollment
        
        This method ensures all active classes have corresponding attendance records
        and removes attendance records for inactive classes.
        
        Args:
            enrollment (Enrollment): The enrollment to sync
            
        Returns:
            dict: Result with sync statistics
        """
        if enrollment.status != 'confirmed':
            return {
                'status': 'skipped',
                'message': 'Only confirmed enrollments are synced'
            }
        
        # Get all active classes for this course
        active_classes = enrollment.course.classes.filter(is_active=True)
        eligible_classes = []
        eligible_class_ids = []
        for class_instance in active_classes:
            if EnrollmentAttendanceService._is_class_within_window(enrollment, class_instance):
                eligible_classes.append(class_instance)
                eligible_class_ids.append(class_instance.id)
        
        # Get existing attendance records for this student in this course
        existing_attendance = Attendance.objects.filter(
            student=enrollment.student,
            class_instance__course=enrollment.course
        )
        
        created_count = 0
        removed_count = 0
        
        try:
            with transaction.atomic():
                # Create missing attendance records for eligible classes
                for class_instance in eligible_classes:
                    attendance_record, created = Attendance.objects.get_or_create(
                        student=enrollment.student,
                        class_instance=class_instance,
                        defaults={
                            'status': 'unmarked',
                            'attendance_time': class_instance.get_class_datetime()
                        }
                    )
                    if created:
                        created_count += 1
                
                # Remove attendance records outside the active window or for inactive classes
                attendance_to_remove = existing_attendance.exclude(
                    class_instance_id__in=eligible_class_ids
                )
                removed_count = attendance_to_remove.count()
                attendance_to_remove.delete()
            
            logger.info(
                f"Synced attendance for {enrollment.student.get_full_name()} "
                f"in {enrollment.course.name}: +{created_count}, -{removed_count}"
            )
            
            return {
                'status': 'success',
                'created_count': created_count,
                'removed_count': removed_count,
                'message': f'Sync completed: created {created_count}, removed {removed_count}'
            }
            
        except Exception as e:
            error_msg = f"Error syncing attendance for enrollment {enrollment.id}: {str(e)}"
            logger.error(error_msg)
            return {
                'status': 'error',
                'message': error_msg
            }


class ClassAttendanceService:
    """Service for managing attendance automation related to classes"""
    
    @staticmethod
    def auto_create_attendance_for_class(class_instance):
        """
        Create attendance records for a new class across all confirmed enrollments
        
        Args:
            class_instance (Class): The newly created class
            
        Returns:
            dict: Result with status, created_count, and message
        """
        if not class_instance.is_active:
            return {
                'status': 'skipped',
                'created_count': 0,
                'message': 'Class is not active'
            }
        
        # Get all confirmed enrollments for this course
        confirmed_enrollments = class_instance.course.enrollments.filter(status='confirmed')
        
        if not confirmed_enrollments.exists():
            return {
                'status': 'success',
                'created_count': 0,
                'message': 'No confirmed enrollments found for course'
            }
        
        created_count = 0
        errors = []
        
        try:
            with transaction.atomic():
                for enrollment in confirmed_enrollments:
                    if not EnrollmentAttendanceService._is_class_within_window(enrollment, class_instance):
                        continue
                    try:
                        attendance_record, created = Attendance.objects.get_or_create(
                            student=enrollment.student,
                            class_instance=class_instance,
                            defaults={
                                'status': 'unmarked',  # Default status
                                'attendance_time': class_instance.get_class_datetime()
                            }
                        )
                        
                        if created:
                            created_count += 1
                            logger.debug(
                                f"Created attendance record for {enrollment.student.get_full_name()} "
                                f"in new class {class_instance} on {class_instance.date}"
                            )
                    
                    except Exception as e:
                        error_msg = f"Error creating attendance for student {enrollment.student.id}: {str(e)}"
                        errors.append(error_msg)
                        logger.error(error_msg)
            
            message = f"Created {created_count} attendance records"
            if errors:
                message += f" with {len(errors)} errors"
            
            logger.info(
                f"Auto-created {created_count} attendance records for class "
                f"{class_instance} on {class_instance.date}"
            )
            
            return {
                'status': 'success',
                'created_count': created_count,
                'message': message,
                'errors': errors
            }
            
        except Exception as e:
            error_msg = f"Transaction failed while creating attendance records: {str(e)}"
            logger.error(error_msg)
            return {
                'status': 'error',
                'created_count': 0,
                'message': error_msg
            }
    
    @staticmethod
    def sync_class_attendance(class_instance):
        """
        Synchronize attendance records for a class
        
        This method ensures all confirmed enrollments have corresponding attendance records
        and removes attendance records for cancelled enrollments.
        
        Args:
            class_instance (Class): The class to sync
            
        Returns:
            dict: Result with sync statistics
        """
        if not class_instance.is_active:
            return {
                'status': 'skipped',
                'message': 'Only active classes are synced'
            }
        
        # Get all confirmed enrollments for this course
        confirmed_enrollments = class_instance.course.enrollments.filter(status='confirmed')
        eligible_enrollments = [
            enrollment
            for enrollment in confirmed_enrollments
            if EnrollmentAttendanceService._is_class_within_window(enrollment, class_instance)
        ]
        
        # Get existing attendance records for this class
        existing_attendance = Attendance.objects.filter(class_instance=class_instance)
        
        created_count = 0
        removed_count = 0
        
        try:
            with transaction.atomic():
                # Create missing attendance records for eligible enrollments
                for enrollment in eligible_enrollments:
                    attendance_record, created = Attendance.objects.get_or_create(
                        student=enrollment.student,
                        class_instance=class_instance,
                        defaults={
                            'status': 'unmarked',
                            'attendance_time': class_instance.get_class_datetime()
                        }
                    )
                    if created:
                        created_count += 1
                
                # Remove attendance records for students who are not eligible for this class
                eligible_student_ids = [enrollment.student_id for enrollment in eligible_enrollments]
                orphaned_attendance = existing_attendance.exclude(student_id__in=eligible_student_ids)
                removed_count = orphaned_attendance.count()
                orphaned_attendance.delete()
            
            logger.info(
                f"Synced attendance for class {class_instance} on {class_instance.date}: "
                f"+{created_count}, -{removed_count}"
            )
            
            return {
                'status': 'success',
                'created_count': created_count,
                'removed_count': removed_count,
                'message': f'Sync completed: created {created_count}, removed {removed_count}'
            }
            
        except Exception as e:
            error_msg = f"Error syncing attendance for class {class_instance.id}: {str(e)}"
            logger.error(error_msg)
            return {
                'status': 'error',
                'message': error_msg
            }


class AttendanceSyncService:
    """Service for bulk attendance synchronization operations"""
    
    @staticmethod
    def sync_all_course_attendance(course):
        """
        Synchronize all attendance records for a course
        
        Args:
            course (Course): The course to sync
            
        Returns:
            dict: Result with comprehensive sync statistics
        """
        total_created = 0
        total_removed = 0
        errors = []
        
        try:
            # Sync all confirmed enrollments
            confirmed_enrollments = course.enrollments.filter(status='confirmed')
            for enrollment in confirmed_enrollments:
                result = EnrollmentAttendanceService.sync_enrollment_attendance(enrollment)
                if result['status'] == 'success':
                    total_created += result.get('created_count', 0)
                    total_removed += result.get('removed_count', 0)
                elif result['status'] == 'error':
                    errors.append(f"Enrollment {enrollment.id}: {result['message']}")
            
            # Sync all active classes
            active_classes = course.classes.filter(is_active=True)
            for class_instance in active_classes:
                result = ClassAttendanceService.sync_class_attendance(class_instance)
                if result['status'] == 'success':
                    total_created += result.get('created_count', 0)
                    total_removed += result.get('removed_count', 0)
                elif result['status'] == 'error':
                    errors.append(f"Class {class_instance.id}: {result['message']}")
            
            logger.info(
                f"Synced all attendance for course {course.name}: "
                f"+{total_created}, -{total_removed}, {len(errors)} errors"
            )
            
            return {
                'status': 'success',
                'total_created': total_created,
                'total_removed': total_removed,
                'errors': errors,
                'message': f'Course sync completed: created {total_created}, removed {total_removed}'
            }
            
        except Exception as e:
            error_msg = f"Error syncing course {course.id}: {str(e)}"
            logger.error(error_msg)
            return {
                'status': 'error',
                'message': error_msg
            }
    
    @staticmethod
    def sync_all_attendance():
        """
        Synchronize all attendance records in the system
        
        Returns:
            dict: Result with system-wide sync statistics
        """
        total_created = 0
        total_removed = 0
        processed_courses = 0
        errors = []
        
        try:
            # Get all courses with enrollments or classes
            courses_with_activity = Course.objects.filter(
                models.Q(enrollments__isnull=False) | 
                models.Q(classes__isnull=False)
            ).distinct()
            
            for course in courses_with_activity:
                result = AttendanceSyncService.sync_all_course_attendance(course)
                processed_courses += 1
                
                if result['status'] == 'success':
                    total_created += result.get('total_created', 0)
                    total_removed += result.get('total_removed', 0)
                    errors.extend(result.get('errors', []))
                elif result['status'] == 'error':
                    errors.append(f"Course {course.id}: {result['message']}")
            
            logger.info(
                f"Synced all system attendance: {processed_courses} courses, "
                f"+{total_created}, -{total_removed}, {len(errors)} errors"
            )
            
            return {
                'status': 'success',
                'processed_courses': processed_courses,
                'total_created': total_created,
                'total_removed': total_removed,
                'errors': errors,
                'message': f'System sync completed: {processed_courses} courses, '
                          f'created {total_created}, removed {total_removed}'
            }
            
        except Exception as e:
            error_msg = f"Error syncing all attendance: {str(e)}"
            logger.error(error_msg)
            return {
                'status': 'error',
                'message': error_msg
            }
