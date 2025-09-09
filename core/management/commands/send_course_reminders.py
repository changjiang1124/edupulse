"""
Management command to send course reminders
This can be run daily via cron job to send automated reminders
"""
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from datetime import timedelta
from core.services import NotificationService
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Send course reminder emails to students'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days-ahead',
            type=int,
            default=1,
            help='Number of days ahead to send reminders for (default: 1)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Preview what would be sent without actually sending emails'
        )

    def handle(self, *args, **options):
        days_ahead = options['days_ahead']
        dry_run = options['dry_run']
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Starting course reminder process for classes {days_ahead} day(s) ahead...'
            )
        )
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING('DRY RUN MODE - No emails will be sent')
            )
        
        try:
            if dry_run:
                # Preview mode - show what would be sent
                sent_count = self._preview_reminders(days_ahead)
            else:
                # Actually send reminders
                sent_count = NotificationService.send_bulk_course_reminders(days_ahead)
            
            if sent_count > 0:
                action = "Would send" if dry_run else "Successfully sent"
                self.stdout.write(
                    self.style.SUCCESS(
                        f'{action} {sent_count} course reminder email(s)'
                    )
                )
            else:
                self.stdout.write(
                    self.style.WARNING('No course reminders to send')
                )
                
        except Exception as e:
            logger.error(f'Error in send_course_reminders command: {str(e)}')
            raise CommandError(f'Failed to send course reminders: {str(e)}')
    
    def _preview_reminders(self, days_ahead):
        """Preview what reminders would be sent without actually sending them"""
        from academics.models import Class
        from enrollment.models import Enrollment
        
        # Get target date
        target_date = timezone.now().date() + timedelta(days=days_ahead)
        
        # Get classes happening on target date
        classes = Class.objects.filter(
            date=target_date,
            is_active=True
        ).select_related('course', 'facility', 'classroom', 'teacher')
        
        total_reminders = 0
        
        self.stdout.write(
            f'\nClasses scheduled for {target_date.strftime("%A, %d %B %Y")}:'
        )
        
        if not classes.exists():
            self.stdout.write('  No classes scheduled for this date')
            return 0
        
        for class_instance in classes:
            self.stdout.write(
                f'\n📚 {class_instance.course.name}'
            )
            self.stdout.write(
                f'   Time: {class_instance.start_time.strftime("%I:%M %p")}'
            )
            self.stdout.write(
                f'   Instructor: {class_instance.teacher.get_full_name()}'
            )
            if class_instance.facility:
                self.stdout.write(
                    f'   Location: {class_instance.facility.name}'
                )
            
            # Get enrolled students for this class
            enrollments = Enrollment.objects.filter(
                course=class_instance.course,
                status='confirmed'
            ).select_related('student')
            
            reminder_count = enrollments.count()
            total_reminders += reminder_count
            
            self.stdout.write(
                f'   📧 Reminders to send: {reminder_count}'
            )
            
            if reminder_count > 0:
                self.stdout.write('   Students:')
                for enrollment in enrollments:
                    student = enrollment.student
                    email = student.contact_email
                    self.stdout.write(
                        f'     • {student.get_full_name()} ({email})'
                    )
        
        return total_reminders