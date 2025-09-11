"""
Django management command to sync attendance records

This command ensures all confirmed enrollments have attendance records
for all active classes in their respective courses.
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db import models
from enrollment.services import AttendanceSyncService
from enrollment.models import Enrollment, Attendance
from academics.models import Course, Class
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Sync attendance records for all confirmed enrollments and active classes'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--course-id',
            type=int,
            help='Sync attendance for a specific course only'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without making changes'
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show detailed output'
        )
    
    def handle(self, *args, **options):
        verbosity = options.get('verbosity', 1)
        dry_run = options.get('dry_run', False)
        course_id = options.get('course_id')
        verbose = options.get('verbose', False)
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING('DRY RUN MODE - No changes will be made')
            )
        
        try:
            if course_id:
                # Sync specific course
                course = Course.objects.get(pk=course_id)
                self.stdout.write(f'Syncing attendance for course: {course.name}')
                
                if dry_run:
                    result = self._dry_run_course_sync(course, verbose)
                else:
                    result = AttendanceSyncService.sync_all_course_attendance(course)
                
                self._display_result(result, course.name)
                
            else:
                # Sync all courses
                self.stdout.write('Syncing attendance for all courses...')
                
                if dry_run:
                    result = self._dry_run_all_sync(verbose)
                else:
                    result = AttendanceSyncService.sync_all_attendance()
                
                self._display_result(result, 'all courses')
        
        except Course.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'Course with ID {course_id} not found')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error during sync: {str(e)}')
            )
            if verbosity >= 2:
                import traceback
                self.stdout.write(traceback.format_exc())
    
    def _dry_run_course_sync(self, course, verbose):
        """Simulate sync for a specific course"""
        confirmed_enrollments = course.enrollments.filter(status='confirmed')
        active_classes = course.classes.filter(is_active=True)
        
        missing_records = []
        
        for enrollment in confirmed_enrollments:
            for class_instance in active_classes:
                exists = Attendance.objects.filter(
                    student=enrollment.student,
                    class_instance=class_instance
                ).exists()
                
                if not exists:
                    missing_records.append({
                        'student': enrollment.student.get_full_name(),
                        'class': f"{class_instance.date} {class_instance.start_time}",
                        'course': course.name
                    })
        
        if verbose and missing_records:
            self.stdout.write('\nMissing attendance records:')
            for record in missing_records:
                self.stdout.write(
                    f"  - {record['student']} -> {record['class']}"
                )
        
        return {
            'status': 'success',
            'total_created': len(missing_records),
            'total_removed': 0,
            'message': f'Would create {len(missing_records)} attendance records'
        }
    
    def _dry_run_all_sync(self, verbose):
        """Simulate sync for all courses"""
        courses = Course.objects.filter(
            models.Q(enrollments__status='confirmed') | 
            models.Q(classes__is_active=True)
        ).distinct()
        
        total_missing = 0
        
        for course in courses:
            result = self._dry_run_course_sync(course, False)
            total_missing += result['total_created']
            
            if verbose and result['total_created'] > 0:
                self.stdout.write(
                    f"Course '{course.name}': {result['total_created']} missing records"
                )
        
        return {
            'status': 'success',
            'processed_courses': courses.count(),
            'total_created': total_missing,
            'total_removed': 0,
            'message': f'Would create {total_missing} attendance records across {courses.count()} courses'
        }
    
    def _display_result(self, result, scope):
        """Display sync results"""
        if result['status'] == 'success':
            self.stdout.write(
                self.style.SUCCESS(f'✓ Sync completed for {scope}')
            )
            
            if 'processed_courses' in result:
                self.stdout.write(f'  Processed courses: {result["processed_courses"]}')
            
            if 'total_created' in result:
                self.stdout.write(f'  Records created: {result["total_created"]}')
            
            if 'total_removed' in result:
                self.stdout.write(f'  Records removed: {result["total_removed"]}')
            
            if result.get('errors'):
                self.stdout.write(
                    self.style.WARNING(f'  Errors encountered: {len(result["errors"])}')
                )
                for error in result['errors'][:5]:  # Show first 5 errors
                    self.stdout.write(f'    - {error}')
                
                if len(result['errors']) > 5:
                    self.stdout.write(f'    ... and {len(result["errors"]) - 5} more')
        
        else:
            self.stdout.write(
                self.style.ERROR(f'✗ Sync failed for {scope}: {result["message"]}')
            )