"""
Management command to check and update early bird pricing that has expired
This command should be run daily to ensure WooCommerce reflects current pricing
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from academics.models import Course
from core.woocommerce_api import WooCommerceSyncService
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Check for expired early bird pricing and update WooCommerce accordingly'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be updated without making changes',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force sync all courses with early bird pricing, regardless of expiry',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        force_sync = options['force']

        self.stdout.write(
            self.style.SUCCESS(f'Starting early bird pricing update check (dry_run={dry_run})')
        )

        # Get all courses with early bird pricing
        courses_with_early_bird = Course.objects.filter(
            early_bird_price__isnull=False,
            early_bird_deadline__isnull=False,
            status='published'
        )

        if not courses_with_early_bird.exists():
            self.stdout.write(
                self.style.WARNING('No courses found with early bird pricing configured.')
            )
            return

        today = timezone.now().date()
        sync_service = WooCommerceSyncService()

        courses_to_sync = []

        for course in courses_with_early_bird:
            # Check if early bird pricing has expired or force sync is enabled
            should_sync = force_sync or (course.early_bird_deadline < today)

            if should_sync:
                courses_to_sync.append(course)

                if course.early_bird_deadline < today:
                    self.stdout.write(
                        f'Early bird expired: {course.name} (deadline was {course.early_bird_deadline})'
                    )
                else:
                    self.stdout.write(
                        f'Force sync: {course.name} (deadline: {course.early_bird_deadline})'
                    )

        if not courses_to_sync:
            self.stdout.write(
                self.style.SUCCESS('No courses need early bird pricing updates.')
            )
            return

        self.stdout.write(
            f'Found {len(courses_to_sync)} courses that need pricing updates.'
        )

        if dry_run:
            self.stdout.write(
                self.style.WARNING('DRY RUN: No actual changes will be made.')
            )
            for course in courses_to_sync:
                self.stdout.write(f'  - Would sync: {course.name}')
            return

        # Perform actual synchronization
        success_count = 0
        error_count = 0

        for course in courses_to_sync:
            try:
                self.stdout.write(f'Syncing {course.name}...', ending=' ')

                if not course.external_id:
                    self.stdout.write(
                        self.style.WARNING('SKIPPED (no WooCommerce product ID)')
                    )
                    continue

                result = sync_service.sync_course_to_woocommerce(course, log_sync=True)

                if result['status'] == 'success':
                    self.stdout.write(self.style.SUCCESS('SUCCESS'))
                    success_count += 1
                else:
                    self.stdout.write(
                        self.style.ERROR(f'FAILED: {result.get("message", "Unknown error")}')
                    )
                    error_count += 1

            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'FAILED: {str(e)}')
                )
                error_count += 1
                logger.error(f'Error syncing course {course.id}: {str(e)}')

        # Summary
        self.stdout.write('')
        self.stdout.write(
            self.style.SUCCESS(
                f'Early bird pricing update completed: {success_count} successful, {error_count} failed'
            )
        )

        if error_count > 0:
            self.stdout.write(
                self.style.WARNING(
                    'Some courses failed to sync. Check the logs for details.'
                )
            )