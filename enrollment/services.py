"""
Service layer for enrollment and attendance automation

This module provides services for managing automatic attendance creation
and synchronization between enrollments, classes, and attendance records.
"""
from django.db import transaction
from django.utils import timezone
from django.db import models
from django.core.exceptions import ValidationError
from .models import Enrollment, Attendance, MakeupSession
from academics.models import Class, Course
from students.models import Student
import logging

logger = logging.getLogger(__name__)


class AttendanceRosterService:
    """Resolve the effective attendance roster for a class."""

    ACTIVE_MAKEUP_STATUSES = ('scheduled', 'completed')
    SYNC_MAKEUP_STATUSES = ('scheduled', 'completed', 'no_show')

    @staticmethod
    def get_roster_entries(class_instance):
        roster = {}

        confirmed_enrollments = class_instance.course.enrollments.filter(
            status='confirmed'
        ).select_related('student')

        for enrollment in confirmed_enrollments:
            if not EnrollmentAttendanceService._is_class_within_window(enrollment, class_instance):
                continue

            student = enrollment.student
            entry = roster.setdefault(
                student.id,
                {
                    'student': student,
                    'from_enrollment': False,
                    'from_makeup': False,
                    'makeup_status': None,
                    'makeup_session_id': None,
                }
            )
            entry['from_enrollment'] = True

        makeup_sessions = MakeupSession.objects.filter(
            target_class=class_instance,
            status__in=AttendanceRosterService.ACTIVE_MAKEUP_STATUSES
        ).select_related('student')

        for makeup in makeup_sessions:
            student = makeup.student
            entry = roster.setdefault(
                student.id,
                {
                    'student': student,
                    'from_enrollment': False,
                    'from_makeup': False,
                    'makeup_status': None,
                    'makeup_session_id': None,
                }
            )
            entry['from_makeup'] = True
            entry['makeup_status'] = makeup.status
            entry['makeup_session_id'] = makeup.id

        return sorted(
            roster.values(),
            key=lambda item: (item['student'].first_name.lower(), item['student'].last_name.lower())
        )

    @staticmethod
    def get_roster_students(class_instance):
        return [entry['student'] for entry in AttendanceRosterService.get_roster_entries(class_instance)]

    @staticmethod
    def get_roster_student_ids(class_instance):
        return [entry['student'].id for entry in AttendanceRosterService.get_roster_entries(class_instance)]


class MakeupSessionService:
    """Create and maintain makeup sessions with attendance side effects."""

    SOURCE_ABSENT_STATUSES = {'unmarked', 'absent'}
    FINAL_STATUSES = {'completed', 'cancelled', 'no_show'}
    ATTENDANCE_STATUS_TO_MAKEUP_STATUS = {
        'present': 'completed',
        'late': 'completed',
        'early_leave': 'completed',
        'absent': 'no_show',
    }

    @staticmethod
    def format_class_label(class_instance):
        return (
            f"{class_instance.course.name} | "
            f"{class_instance.date.strftime('%a %d/%m/%Y')} "
            f"{class_instance.start_time.strftime('%I:%M %p')}"
        )

    @staticmethod
    def get_student_meta(student):
        active_enrollments = Enrollment.objects.filter(
            student=student,
            status__in=['pending', 'confirmed']
        ).select_related('course').order_by('course__name')

        course_names = []
        seen = set()
        for enrollment in active_enrollments:
            if enrollment.course_id in seen:
                continue
            seen.add(enrollment.course_id)
            course_names.append(enrollment.course.name)

        return {
            'id': student.id,
            'name': student.get_full_name(),
            'email': student.contact_email or '',
            'phone': student.contact_phone or '',
            'active_courses': course_names,
        }

    @staticmethod
    def get_candidate_classes(student, current_class, initiated_from='source', actor=None):
        local_now = timezone.localtime()
        now_date = local_now.date()
        now_time = local_now.time()

        if initiated_from == 'target':
            # Source classes stay student-related and can include past sessions.
            enrollment_course_ids = set(
                Enrollment.objects.filter(
                    student=student,
                    status__in=['pending', 'confirmed']
                ).values_list('course_id', flat=True)
            )
            attendance_class_ids = set(
                Attendance.objects.filter(
                    student=student
                ).values_list('class_instance_id', flat=True)
            )
            makeup_class_ids = set(
                MakeupSession.objects.filter(
                    student=student
                ).values_list('source_class_id', flat=True)
            )
            makeup_class_ids.update(
                MakeupSession.objects.filter(
                    student=student
                ).values_list('target_class_id', flat=True)
            )

            queryset = Class.objects.filter(
                is_active=True
            ).filter(
                models.Q(course_id__in=enrollment_course_ids) |
                models.Q(id__in=attendance_class_ids) |
                models.Q(id__in=makeup_class_ids)
            )
        else:
            # Target classes are globally available upcoming sessions.
            queryset = Class.objects.filter(
                is_active=True
            ).filter(
                models.Q(date__gt=now_date) |
                models.Q(date=now_date, start_time__gte=now_time)
            )

        queryset = queryset.select_related('course').distinct().order_by('date', 'start_time', 'course__name')

        if (
            actor is not None
            and hasattr(actor, 'role')
            and actor.role == 'teacher'
        ):
            queryset = queryset.filter(course__teacher=actor)

        candidates = []
        for class_instance in queryset:
            if class_instance.id == current_class.id:
                continue
            candidates.append({
                'id': class_instance.id,
                'course_name': class_instance.course.name,
                'date': class_instance.date.isoformat(),
                'start_time': class_instance.start_time.isoformat(),
                'label': MakeupSessionService.format_class_label(class_instance),
            })

        return {
            'initiated_from': initiated_from,
            'student': MakeupSessionService.get_student_meta(student),
            'current_class': {
                'id': current_class.id,
                'label': MakeupSessionService.format_class_label(current_class),
            },
            'candidates': candidates,
        }

    @staticmethod
    def _validate_student_relationship(student, source_class):
        has_enrollment = Enrollment.objects.filter(
            student=student,
            course=source_class.course,
            status__in=['pending', 'confirmed']
        ).exists()
        has_source_attendance = Attendance.objects.filter(
            student=student,
            class_instance=source_class
        ).exists()

        if not has_enrollment and not has_source_attendance:
            raise ValidationError(
                'Student is not linked to the source course. '
                'Please enrol the student first or confirm source attendance.'
            )

    @staticmethod
    def _validate_class_pair(source_class, target_class):
        local_now = timezone.localtime()

        if not target_class.is_active:
            raise ValidationError('Target class must be active.')

        if target_class.get_class_datetime() <= local_now:
            raise ValidationError('Target class must be in the future and not started yet.')

    @staticmethod
    def update_session_status(*, makeup_session, new_status, actor=None, note=''):
        if new_status not in MakeupSessionService.FINAL_STATUSES:
            raise ValidationError('Invalid makeup status update.')

        if makeup_session.status != 'scheduled':
            if makeup_session.status == new_status:
                return makeup_session
            raise ValidationError('Only scheduled makeup sessions can be updated.')

        note = (note or '').strip()
        if new_status == 'cancelled' and not note:
            raise ValidationError('Cancellation reason is required.')

        actor_label = 'System'
        if actor is not None:
            actor_label = actor.get_full_name().strip() or actor.username

        timestamp = timezone.localtime().strftime('%Y-%m-%d %H:%M')
        audit_note = f'[{timestamp}] Status changed to {new_status} by {actor_label}'
        if note:
            audit_note = f'{audit_note}: {note}'

        makeup_session.status = new_status
        makeup_session.updated_by = actor
        makeup_session.notes = (
            f'{makeup_session.notes}\n{audit_note}'.strip()
            if makeup_session.notes else
            audit_note
        )
        makeup_session.save(update_fields=['status', 'updated_by', 'notes', 'updated_at'])
        return makeup_session

    @staticmethod
    def sync_status_from_target_attendance(*, student, target_class, attendance_status, actor=None):
        next_status = MakeupSessionService.ATTENDANCE_STATUS_TO_MAKEUP_STATUS.get(attendance_status)
        if not next_status:
            return 0

        scheduled_sessions = MakeupSession.objects.filter(
            student=student,
            target_class=target_class,
            status='scheduled'
        )

        updated_count = 0
        for makeup_session in scheduled_sessions:
            MakeupSessionService.update_session_status(
                makeup_session=makeup_session,
                new_status=next_status,
                actor=actor,
                note=f'Auto-sync from attendance status: {attendance_status}.',
            )
            updated_count += 1

        return updated_count

    @staticmethod
    def schedule_session(
        *,
        student,
        source_class,
        target_class,
        initiated_from='source',
        reason_type='student_request',
        notes='',
        actor=None
    ):
        if source_class.pk == target_class.pk:
            raise ValidationError('Source and target classes must be different.')

        MakeupSessionService._validate_student_relationship(student, source_class)
        MakeupSessionService._validate_class_pair(source_class, target_class)

        with transaction.atomic():
            makeup_session = MakeupSession.objects.create(
                student=student,
                source_class=source_class,
                target_class=target_class,
                initiated_from=initiated_from,
                reason_type=reason_type,
                notes=notes or '',
                created_by=actor,
                updated_by=actor,
                status='scheduled',
            )

            source_attendance, _ = Attendance.objects.get_or_create(
                student=student,
                class_instance=source_class,
                defaults={
                    'status': 'unmarked',
                    'attendance_time': source_class.get_class_datetime()
                }
            )

            source_warning = None
            local_now = timezone.localtime()
            if source_class.get_class_datetime() <= local_now:
                if source_attendance.status in MakeupSessionService.SOURCE_ABSENT_STATUSES:
                    if source_attendance.status != 'absent':
                        source_attendance.status = 'absent'
                        source_attendance.save(update_fields=['status', 'updated_at'])
                elif source_attendance.status in ['present', 'late', 'early_leave']:
                    source_warning = (
                        'Source attendance is already marked as '
                        f'{source_attendance.get_status_display()}; it was not overwritten.'
                    )
            else:
                source_warning = (
                    'Source class is in the future, so attendance was not auto-marked absent.'
                )

            target_attendance, target_created = Attendance.objects.get_or_create(
                student=student,
                class_instance=target_class,
                defaults={
                    'status': 'unmarked',
                    'attendance_time': target_class.get_class_datetime()
                }
            )

            return {
                'makeup_session': makeup_session,
                'source_attendance': source_attendance,
                'target_attendance': target_attendance,
                'target_created': target_created,
                'source_warning': source_warning,
            }


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
        
        # Get active makeup sessions pointing to this class
        active_makeups = MakeupSession.objects.filter(
            target_class=class_instance,
            status__in=AttendanceRosterService.SYNC_MAKEUP_STATUSES
        ).select_related('student')

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

                # Ensure makeup students also keep an attendance record
                for makeup_session in active_makeups:
                    attendance_record, created = Attendance.objects.get_or_create(
                        student=makeup_session.student,
                        class_instance=class_instance,
                        defaults={
                            'status': 'unmarked',
                            'attendance_time': class_instance.get_class_datetime()
                        }
                    )
                    if created:
                        created_count += 1
                
                # Remove attendance records for students who are not eligible for this class
                eligible_student_ids = {
                    enrollment.student_id for enrollment in eligible_enrollments
                }
                eligible_student_ids.update(
                    makeup_session.student_id for makeup_session in active_makeups
                )
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
