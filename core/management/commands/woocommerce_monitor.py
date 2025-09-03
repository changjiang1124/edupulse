"""
Django management command for WooCommerce synchronization monitoring and management
"""
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.db.models import Count, Q
from core.models import WooCommerceSyncLog, WooCommerceSyncQueue
from core.woocommerce_api import WooCommerceSyncService
from academics.models import Course
from datetime import timedelta
import json


class Command(BaseCommand):
    help = 'Monitor and manage WooCommerce synchronization status'

    def add_arguments(self, parser):
        parser.add_argument(
            '--status',
            action='store_true',
            help='Show overall synchronization status',
        )
        parser.add_argument(
            '--health-check',
            action='store_true',
            help='Perform WooCommerce API health check',
        )
        parser.add_argument(
            '--sync-report',
            action='store_true',
            help='Generate detailed sync report',
        )
        parser.add_argument(
            '--failed-syncs',
            action='store_true',
            help='Show all failed synchronizations',
        )
        parser.add_argument(
            '--retry-failed',
            action='store_true',
            help='Retry all retryable failed synchronizations',
        )
        parser.add_argument(
            '--process-queue',
            action='store_true',
            help='Process pending queue items',
        )
        parser.add_argument(
            '--cleanup',
            type=int,
            metavar='DAYS',
            help='Clean up sync logs older than specified days',
        )
        parser.add_argument(
            '--course-id',
            type=int,
            metavar='ID',
            help='Specify course ID for course-specific operations',
        )

    def handle(self, *args, **options):
        if options['status']:
            self.show_status()
        elif options['health_check']:
            self.health_check()
        elif options['sync_report']:
            self.sync_report(options.get('course_id'))
        elif options['failed_syncs']:
            self.show_failed_syncs()
        elif options['retry_failed']:
            self.retry_failed_syncs()
        elif options['process_queue']:
            self.process_queue()
        elif options['cleanup']:
            self.cleanup_logs(options['cleanup'])
        else:
            self.stdout.write(
                self.style.ERROR('Please specify an action. Use --help for options.')
            )

    def show_status(self):
        """Show overall synchronization status"""
        self.stdout.write(self.style.SUCCESS('\n=== WooCommerce Sync Status ===\n'))
        
        # Course sync status
        total_courses = Course.objects.filter(status='published').count()
        synced_courses = Course.objects.filter(status='published', external_id__isnull=False).count()
        unsynced_courses = total_courses - synced_courses
        
        self.stdout.write(f"📊 Course Synchronization:")
        self.stdout.write(f"   • Total published courses: {total_courses}")
        self.stdout.write(f"   • Synced to WooCommerce: {synced_courses}")
        self.stdout.write(f"   • Not synced: {unsynced_courses}")
        
        # Sync logs summary
        now = timezone.now()
        today = now.date()
        
        recent_logs = WooCommerceSyncLog.objects.filter(
            created_at__date=today
        ).aggregate(
            total=Count('id'),
            success=Count('id', filter=Q(status='success')),
            failed=Count('id', filter=Q(status='failed')),
            processing=Count('id', filter=Q(status='processing'))
        )
        
        self.stdout.write(f"\n📈 Today's Sync Activity:")
        self.stdout.write(f"   • Total syncs: {recent_logs['total']}")
        self.stdout.write(f"   • Successful: {recent_logs['success']}")
        self.stdout.write(f"   • Failed: {recent_logs['failed']}")
        self.stdout.write(f"   • In progress: {recent_logs['processing']}")
        
        # Queue status
        queue_stats = WooCommerceSyncQueue.objects.aggregate(
            total=Count('id'),
            queued=Count('id', filter=Q(status='queued')),
            processing=Count('id', filter=Q(status='processing')),
            failed=Count('id', filter=Q(status='failed'))
        )
        
        self.stdout.write(f"\n⏳ Queue Status:")
        self.stdout.write(f"   • Total queue items: {queue_stats['total']}")
        self.stdout.write(f"   • Queued: {queue_stats['queued']}")
        self.stdout.write(f"   • Processing: {queue_stats['processing']}")
        self.stdout.write(f"   • Failed: {queue_stats['failed']}")

    def health_check(self):
        """Perform WooCommerce API health check"""
        self.stdout.write(self.style.SUCCESS('\n=== WooCommerce Health Check ===\n'))
        
        try:
            sync_service = WooCommerceSyncService()
            result = sync_service.test_api_connection()
            
            if result['status'] == 'success':
                self.stdout.write(self.style.SUCCESS('✅ WooCommerce API is healthy'))
                if result.get('data', {}).get('environment'):
                    env = result['data']['environment']
                    self.stdout.write(f"   • WooCommerce Version: {env.get('version', 'Unknown')}")
                    self.stdout.write(f"   • WordPress Version: {env.get('wp_version', 'Unknown')}")
                    self.stdout.write(f"   • PHP Version: {env.get('php_version', 'Unknown')}")
            else:
                self.stdout.write(self.style.ERROR('❌ WooCommerce API health check failed'))
                self.stdout.write(f"   Error: {result.get('message', 'Unknown error')}")
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Health check failed with exception: {str(e)}'))

    def sync_report(self, course_id=None):
        """Generate detailed sync report"""
        if course_id:
            self.stdout.write(self.style.SUCCESS(f'\n=== Sync Report for Course ID {course_id} ===\n'))
            try:
                course = Course.objects.get(id=course_id)
                self.show_course_sync_details(course)
            except Course.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'Course with ID {course_id} not found'))
        else:
            self.stdout.write(self.style.SUCCESS('\n=== Detailed Sync Report ===\n'))
            self.show_detailed_report()

    def show_course_sync_details(self, course):
        """Show sync details for a specific course"""
        self.stdout.write(f"📋 Course: {course.name}")
        self.stdout.write(f"   • Status: {course.get_status_display()}")
        self.stdout.write(f"   • Category: {course.get_category_display()}")
        self.stdout.write(f"   • WooCommerce ID: {course.external_id or 'Not synced'}")
        
        # Recent sync logs for this course
        logs = WooCommerceSyncLog.objects.filter(course=course).order_by('-created_at')[:5]
        
        if logs:
            self.stdout.write(f"\n🔄 Recent sync attempts:")
            for log in logs:
                status_emoji = '✅' if log.status == 'success' else '❌' if log.status == 'failed' else '⏳'
                self.stdout.write(
                    f"   {status_emoji} {log.get_sync_type_display()} - "
                    f"{log.get_status_display()} ({log.created_at.strftime('%Y-%m-%d %H:%M')})"
                )
                if log.error_message:
                    self.stdout.write(f"      Error: {log.error_message[:100]}...")
        else:
            self.stdout.write("   No sync attempts found")

    def show_detailed_report(self):
        """Show detailed sync report for all courses"""
        # Performance metrics
        week_ago = timezone.now() - timedelta(days=7)
        
        logs = WooCommerceSyncLog.objects.filter(created_at__gte=week_ago)
        
        if logs.exists():
            avg_duration = logs.exclude(duration_ms__isnull=True).aggregate(
                avg_duration=models.Avg('duration_ms')
            )['avg_duration']
            
            success_rate = logs.filter(status='success').count() / logs.count() * 100
            
            self.stdout.write(f"📊 Performance Metrics (Last 7 days):")
            self.stdout.write(f"   • Average sync duration: {avg_duration:.0f}ms" if avg_duration else "   • Average sync duration: N/A")
            self.stdout.write(f"   • Success rate: {success_rate:.1f}%")
            
            # Error analysis
            failed_logs = logs.filter(status='failed')
            if failed_logs.exists():
                self.stdout.write(f"\n🚨 Common Errors:")
                error_counts = {}
                for log in failed_logs:
                    error = log.error_message[:50] if log.error_message else "Unknown error"
                    error_counts[error] = error_counts.get(error, 0) + 1
                
                for error, count in sorted(error_counts.items(), key=lambda x: x[1], reverse=True)[:5]:
                    self.stdout.write(f"   • {error}: {count} occurrences")

    def show_failed_syncs(self):
        """Show all failed synchronizations"""
        self.stdout.write(self.style.SUCCESS('\n=== Failed Synchronizations ===\n'))
        
        failed_logs = WooCommerceSyncLog.objects.filter(status='failed').order_by('-created_at')
        
        if not failed_logs.exists():
            self.stdout.write(self.style.SUCCESS('✅ No failed synchronizations found'))
            return
        
        for log in failed_logs[:20]:  # Limit to most recent 20
            retry_info = f" (Retry {log.retry_count}/{log.max_retries})" if log.retry_count > 0 else ""
            self.stdout.write(
                f"❌ {log.course_name or 'Unknown Course'} - "
                f"{log.get_sync_type_display()}{retry_info}"
            )
            self.stdout.write(f"   Time: {log.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
            if log.error_message:
                self.stdout.write(f"   Error: {log.error_message[:150]}...")
            self.stdout.write("")

    def retry_failed_syncs(self):
        """Retry all retryable failed synchronizations"""
        self.stdout.write(self.style.SUCCESS('\n=== Retrying Failed Syncs ===\n'))
        
        failed_logs = WooCommerceSyncLog.objects.filter(
            status='failed',
            course__isnull=False
        )
        retryable_logs = [log for log in failed_logs if log.can_retry]
        
        if not retryable_logs:
            self.stdout.write('No retryable failed syncs found')
            return
        
        sync_service = WooCommerceSyncService()
        success_count = 0
        
        for log in retryable_logs:
            self.stdout.write(f"Retrying: {log.course.name}")
            try:
                result = sync_service.sync_course_to_woocommerce(log.course)
                if result['status'] == 'success':
                    success_count += 1
                    self.stdout.write(self.style.SUCCESS(f"   ✅ Success"))
                else:
                    self.stdout.write(self.style.ERROR(f"   ❌ Failed: {result.get('message', 'Unknown error')}"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"   ❌ Exception: {str(e)}"))
        
        self.stdout.write(f"\nRetry completed: {success_count}/{len(retryable_logs)} succeeded")

    def process_queue(self):
        """Process pending queue items"""
        self.stdout.write(self.style.SUCCESS('\n=== Processing Queue ===\n'))
        
        queued_items = WooCommerceSyncQueue.objects.filter(status='queued').order_by('priority', 'scheduled_for')
        ready_items = [item for item in queued_items if item.is_ready]
        
        if not ready_items:
            self.stdout.write('No ready queue items to process')
            return
        
        sync_service = WooCommerceSyncService()
        processed_count = 0
        
        for item in ready_items:
            self.stdout.write(f"Processing: {item.course.name} ({item.get_action_display()})")
            
            item.status = 'processing'
            item.save()
            
            try:
                if item.action == 'sync':
                    result = sync_service.sync_course_to_woocommerce(item.course)
                elif item.action == 'delete':
                    result = sync_service.remove_course_from_woocommerce(item.course)
                else:
                    result = {'status': 'error', 'message': f'Unknown action: {item.action}'}
                
                if result['status'] == 'success':
                    item.status = 'completed'
                    processed_count += 1
                    self.stdout.write(self.style.SUCCESS(f"   ✅ Success"))
                else:
                    item.status = 'failed'
                    item.last_error = result.get('message', 'Unknown error')
                    self.stdout.write(self.style.ERROR(f"   ❌ Failed: {item.last_error}"))
                
                item.attempts += 1
                item.save()
                
            except Exception as e:
                item.status = 'failed'
                item.last_error = str(e)
                item.attempts += 1
                item.save()
                self.stdout.write(self.style.ERROR(f"   ❌ Exception: {str(e)}"))
        
        self.stdout.write(f"\nQueue processing completed: {processed_count}/{len(ready_items)} succeeded")

    def cleanup_logs(self, days):
        """Clean up old sync logs"""
        self.stdout.write(self.style.SUCCESS(f'\n=== Cleaning Up Logs Older Than {days} Days ===\n'))
        
        cutoff_date = timezone.now() - timedelta(days=days)
        
        # Only delete successful logs to preserve error history
        old_logs = WooCommerceSyncLog.objects.filter(
            created_at__lt=cutoff_date,
            status='success'
        )
        
        count = old_logs.count()
        if count > 0:
            old_logs.delete()
            self.stdout.write(self.style.SUCCESS(f"✅ Cleaned up {count} old successful sync logs"))
        else:
            self.stdout.write("No old logs to clean up")
        
        # Clean up completed queue items
        old_queue_items = WooCommerceSyncQueue.objects.filter(
            completed_at__lt=cutoff_date,
            status__in=['completed', 'cancelled']
        )
        
        queue_count = old_queue_items.count()
        if queue_count > 0:
            old_queue_items.delete()
            self.stdout.write(self.style.SUCCESS(f"✅ Cleaned up {queue_count} old queue items"))