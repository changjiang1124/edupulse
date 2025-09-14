"""
Django management command to update expired courses

Usage:
    python manage.py update_expired_courses
    python manage.py update_expired_courses --dry-run
    python manage.py update_expired_courses --check-consistency
"""

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from academics.services import CourseStatusService


class Command(BaseCommand):
    help = 'Update courses that have passed their end date to expired status'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be updated without making changes'
        )
        
        parser.add_argument(
            '--check-consistency',
            action='store_true',
            help='Check for status inconsistencies without updating'
        )
        
        parser.add_argument(
            '--upcoming',
            type=int,
            default=0,
            help='Show courses expiring in N days (default: 0 for today only)'
        )
    
    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('Course Status Update Tool')
        )
        self.stdout.write(f"Run time: {timezone.now()}")
        self.stdout.write("-" * 50)
        
        if options['check_consistency']:
            self.check_consistency()
        elif options['upcoming'] > 0:
            self.show_upcoming_expiry(options['upcoming'])
        else:
            self.update_expired_courses(options['dry_run'])
    
    def update_expired_courses(self, dry_run=False):
        """Update expired courses"""
        self.stdout.write("Checking for courses that need status update...")
        
        result = CourseStatusService.update_expired_courses(dry_run=dry_run)
        
        if result['found_expired'] == 0:
            self.stdout.write(
                self.style.SUCCESS("✅ No courses need status updates")
            )
            return
        
        self.stdout.write(
            f"Found {result['found_expired']} courses that should be expired:"
        )
        
        for course_info in result['courses']:
            status_indicator = "❌" if course_info['current_status'] != 'expired' else "✅"
            self.stdout.write(
                f"  {status_indicator} {course_info['name']} (ID: {course_info['id']}) - "
                f"End date: {course_info['end_date']}, Status: {course_info['current_status']}"
            )
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING(f"DRY RUN: Would update {result['found_expired']} courses")
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f"✅ Updated {result['updated']} courses to expired status")
            )
    
    def check_consistency(self):
        """Check status consistency"""
        self.stdout.write("Checking course status consistency...")
        
        report = CourseStatusService.check_status_consistency()
        
        # Check for courses that should be expired
        if report['should_be_expired']['count'] > 0:
            self.stdout.write(
                self.style.ERROR(
                    f"❌ Found {report['should_be_expired']['count']} published courses that should be expired:"
                )
            )
            for course in report['should_be_expired']['courses']:
                self.stdout.write(
                    f"  • {course['name']} (ID: {course['id']}) - End date: {course['end_date']}"
                )
        else:
            self.stdout.write(
                self.style.SUCCESS("✅ No published courses are incorrectly active")
            )
        
        # Check for courses that might be incorrectly expired
        if report['incorrectly_expired']['count'] > 0:
            self.stdout.write(
                self.style.WARNING(
                    f"⚠️  Found {report['incorrectly_expired']['count']} expired courses that might still be active:"
                )
            )
            for course in report['incorrectly_expired']['courses']:
                self.stdout.write(
                    f"  • {course['name']} (ID: {course['id']}) - End date: {course['end_date']}"
                )
        else:
            self.stdout.write(
                self.style.SUCCESS("✅ No courses are incorrectly expired")
            )
        
        total_issues = report['should_be_expired']['count'] + report['incorrectly_expired']['count']
        
        if total_issues == 0:
            self.stdout.write(
                self.style.SUCCESS("\n🎉 All course statuses are consistent!")
            )
        else:
            self.stdout.write(
                self.style.ERROR(f"\n⚠️  Found {total_issues} status consistency issues")
            )
            self.stdout.write(
                "Run 'python manage.py update_expired_courses' to fix expired courses"
            )
    
    def show_upcoming_expiry(self, days_ahead):
        """Show courses expiring soon"""
        self.stdout.write(f"Checking for courses expiring in the next {days_ahead} days...")
        
        upcoming_courses = CourseStatusService.get_upcoming_expiry(days_ahead)
        
        if upcoming_courses.count() == 0:
            self.stdout.write(
                self.style.SUCCESS(f"✅ No courses expiring in the next {days_ahead} days")
            )
            return
        
        self.stdout.write(
            f"Found {upcoming_courses.count()} courses expiring soon:"
        )
        
        for course in upcoming_courses:
            end_date = course.end_date or course.start_date
            days_until_expiry = (end_date - timezone.now().date()).days
            
            if days_until_expiry == 0:
                urgency = "🔴 TODAY"
            elif days_until_expiry <= 2:
                urgency = "🟡 SOON"
            else:
                urgency = "🟢 UPCOMING"
            
            self.stdout.write(
                f"  {urgency} {course.name} (ID: {course.pk}) - "
                f"Expires: {end_date} ({days_until_expiry} days)"
            )