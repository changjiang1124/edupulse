"""
Course Status Management Service

Centralized service for managing course status updates and consistency checks.
"""

from django.utils import timezone
from django.conf import settings
from django.db.models import Q
from academics.models import Course
from core.woocommerce_api import WooCommerceSyncService
import logging

logger = logging.getLogger(__name__)


class CourseWooCommerceService:
    """Shared helper for explicit course save + WooCommerce sync flows."""

    SIGNAL_SKIP_ATTR = '_skip_woocommerce_sync_signal'

    @classmethod
    def mark_manual_sync(cls, course):
        setattr(course, cls.SIGNAL_SKIP_ATTR, True)

    @classmethod
    def clear_manual_sync(cls, course):
        if hasattr(course, cls.SIGNAL_SKIP_ATTR):
            delattr(course, cls.SIGNAL_SKIP_ATTR)

    @staticmethod
    def should_sync(course):
        return course.status == 'published' or bool(course.external_id)

    @classmethod
    def save_course_and_sync(cls, course, skip_auto_status_update=False):
        if skip_auto_status_update:
            course._skip_auto_status_update = True

        cls.mark_manual_sync(course)
        try:
            course.save()
        finally:
            cls.clear_manual_sync(course)
            if hasattr(course, '_skip_auto_status_update'):
                delattr(course, '_skip_auto_status_update')

        return cls.sync_saved_course(course)

    @classmethod
    def sync_saved_course(cls, course):
        if not cls.should_sync(course):
            return {
                'status': 'skipped',
                'message': 'WooCommerce sync not required for this course.',
            }

        if not getattr(settings, 'WOOCOMMERCE_SYNC_ENABLED', True):
            return {
                'status': 'disabled',
                'message': 'WooCommerce sync is disabled in this environment.',
            }

        try:
            sync_service = WooCommerceSyncService()
            return sync_service.sync_course_to_woocommerce(course)
        except Exception as exc:
            logger.error(f'Error syncing course {course.pk} to WooCommerce: {exc}')
            return {
                'status': 'error',
                'message': str(exc),
            }

    @staticmethod
    def get_success_suffix(course):
        if course.status == 'published':
            return 'WooCommerce is now published.'
        return 'WooCommerce is now saved as Draft.'

    @staticmethod
    def get_failure_message(result):
        message = ((result or {}).get('message') or 'Unknown error').rstrip('.')
        return f'WooCommerce sync failed: {message}. Local course changes were saved.'

    @staticmethod
    def _format_remote_status(raw_status):
        status_map = {
            'publish': {
                'label': 'Published',
                'badge_class': 'bg-success-subtle text-success-emphasis border border-success-subtle',
                'icon': 'fa-globe',
            },
            'draft': {
                'label': 'Draft',
                'badge_class': 'bg-secondary-subtle text-secondary-emphasis border border-secondary-subtle',
                'icon': 'fa-eye-slash',
            },
            'private': {
                'label': 'Private',
                'badge_class': 'bg-warning-subtle text-warning-emphasis border border-warning-subtle',
                'icon': 'fa-lock',
            },
        }
        return status_map.get(
            raw_status,
            {
                'label': 'Unknown',
                'badge_class': 'bg-light text-dark border',
                'icon': 'fa-question-circle',
            },
        )

    @staticmethod
    def _build_health_meta(state):
        health_map = {
            'synced': {
                'label': 'Synced',
                'badge_class': 'bg-success-subtle text-success-emphasis border border-success-subtle',
                'icon': 'fa-check-circle',
            },
            'failed': {
                'label': 'Sync failed',
                'badge_class': 'bg-danger-subtle text-danger-emphasis border border-danger-subtle',
                'icon': 'fa-triangle-exclamation',
            },
            'linked': {
                'label': 'Linked',
                'badge_class': 'bg-warning-subtle text-warning-emphasis border border-warning-subtle',
                'icon': 'fa-link',
            },
            'not_synced': {
                'label': 'Not synced',
                'badge_class': 'bg-secondary-subtle text-secondary-emphasis border border-secondary-subtle',
                'icon': 'fa-minus-circle',
            },
        }
        return health_map[state]

    @classmethod
    def _extract_remote_status(cls, log):
        if not log:
            return None

        response_data = log.response_data or {}
        if isinstance(response_data, dict) and response_data.get('status'):
            return response_data.get('status')

        request_data = log.request_data or {}
        requested_status = request_data.get('status')
        if requested_status == 'published':
            return 'publish'
        if requested_status in {'draft', 'expired', 'archived'}:
            return 'draft'
        return None

    @classmethod
    def build_sync_summary(cls, course, latest_log=None, latest_success_log=None):
        if latest_log is None or latest_success_log is None:
            from core.models import WooCommerceSyncLog

            logs = list(
                WooCommerceSyncLog.objects.filter(course=course)
                .order_by('-created_at', '-pk')[:10]
            )
            latest_log = logs[0] if logs else None
            latest_success_log = next((log for log in logs if log.status == 'success'), None)

        if latest_log and latest_log.status == 'failed':
            health_state = 'failed'
        elif course.external_id and (course.woocommerce_last_synced_at or latest_success_log):
            health_state = 'synced'
        elif course.external_id:
            health_state = 'linked'
        else:
            health_state = 'not_synced'

        health_meta = cls._build_health_meta(health_state)
        raw_remote_status = cls._extract_remote_status(latest_success_log or latest_log)
        remote_status = cls._format_remote_status(raw_remote_status)

        failure_message = ''
        if latest_log and latest_log.status == 'failed':
            failure_message = latest_log.error_message or 'Unknown error'

        return {
            'health_state': health_state,
            'health_label': health_meta['label'],
            'health_badge_class': health_meta['badge_class'],
            'health_icon': health_meta['icon'],
            'remote_status_label': remote_status['label'],
            'remote_status_badge_class': remote_status['badge_class'],
            'remote_status_icon': remote_status['icon'],
            'last_synced_at': course.woocommerce_last_synced_at or getattr(latest_success_log, 'completed_at', None),
            'last_attempt_at': getattr(latest_log, 'last_attempt_at', None),
            'product_id': course.external_id or getattr(latest_success_log, 'wc_product_id', ''),
            'failure_message': failure_message,
            'has_product': bool(course.external_id),
        }

    @classmethod
    def attach_sync_summaries(cls, courses):
        course_list = list(courses)
        course_ids = [course.pk for course in course_list if course.pk]
        if not course_ids:
            return course_list

        from core.models import WooCommerceSyncLog

        latest_logs = {}
        latest_success_logs = {}
        logs = WooCommerceSyncLog.objects.filter(course_id__in=course_ids).order_by('course_id', '-created_at', '-pk')

        for log in logs:
            latest_logs.setdefault(log.course_id, log)
            if log.status == 'success':
                latest_success_logs.setdefault(log.course_id, log)

        for course in course_list:
            course.woocommerce_summary = cls.build_sync_summary(
                course,
                latest_log=latest_logs.get(course.pk),
                latest_success_log=latest_success_logs.get(course.pk),
            )

        return course_list


class CourseStatusService:
    """Service class for managing course status operations"""
    
    @classmethod
    def update_expired_courses(cls, dry_run=False):
        """
        Update courses that should be expired based on end dates
        
        Args:
            dry_run (bool): If True, only return what would be updated without making changes
            
        Returns:
            dict: Summary of updates performed or would be performed
        """
        today = timezone.now().date()
        
        # Find published courses that have passed their end date
        expired_courses = Course.objects.filter(
            status='published',
            end_date__lt=today
        ) | Course.objects.filter(
            status='published',
            end_date__isnull=True,
            start_date__lt=today
        )
        
        expired_count = expired_courses.count()
        
        result = {
            'found_expired': expired_count,
            'updated': 0,
            'courses': []
        }
        
        if expired_count > 0:
            for course in expired_courses:
                end_date = course.end_date or course.start_date
                result['courses'].append({
                    'id': course.pk,
                    'name': course.name,
                    'end_date': end_date,
                    'current_status': course.status
                })
                
                if not dry_run:
                    # Set flag to prevent automatic status update in save()
                    course._skip_auto_status_update = False
                    course.status = 'expired'
                    course.save()
                    result['updated'] += 1
                    logger.info(f"Updated course to expired: {course.name} (ID: {course.pk})")
            
            if not dry_run:
                logger.info(f"Updated {result['updated']} courses to expired status")
        
        return result
    
    @classmethod
    def check_status_consistency(cls):
        """
        Check for courses with inconsistent status
        
        Returns:
            dict: Report of any inconsistencies found
        """
        today = timezone.now().date()
        
        # Find published courses that should be expired
        should_be_expired = Course.objects.filter(
            status='published',
            end_date__lt=today
        ) | Course.objects.filter(
            status='published', 
            end_date__isnull=True,
            start_date__lt=today
        )
        
        # Find expired courses that might not need to be expired
        # (though this is less likely to happen)
        incorrectly_expired = Course.objects.filter(
            status='expired',
            end_date__gte=today
        ) | Course.objects.filter(
            status='expired',
            end_date__isnull=True,
            start_date__gte=today
        )
        
        return {
            'should_be_expired': {
                'count': should_be_expired.count(),
                'courses': [
                    {
                        'id': c.pk,
                        'name': c.name,
                        'end_date': c.end_date or c.start_date,
                        'status': c.status
                    } for c in should_be_expired
                ]
            },
            'incorrectly_expired': {
                'count': incorrectly_expired.count(),
                'courses': [
                    {
                        'id': c.pk,
                        'name': c.name,
                        'end_date': c.end_date or c.start_date,
                        'status': c.status
                    } for c in incorrectly_expired
                ]
            }
        }
    
    @classmethod
    def bulk_update_status(cls, course_ids, new_status, force=False):
        """
        Bulk update course status
        
        Args:
            course_ids (list): List of course IDs to update
            new_status (str): New status to set
            force (bool): If True, skip date validation
            
        Returns:
            dict: Summary of updates
        """
        if new_status not in ['draft', 'published', 'expired']:
            raise ValueError(f"Invalid status: {new_status}")
        
        courses = Course.objects.filter(id__in=course_ids)
        updated_count = 0
        skipped = []
        
        for course in courses:
            # Validate status change if not forced
            if not force and new_status == 'published':
                end_date = course.end_date or course.start_date
                if end_date < timezone.now().date():
                    skipped.append({
                        'id': course.pk,
                        'name': course.name,
                        'reason': 'Cannot publish expired course'
                    })
                    continue
            
            course._skip_auto_status_update = True
            course.status = new_status
            course.save()
            updated_count += 1
            logger.info(f"Bulk updated course status: {course.name} -> {new_status}")
        
        return {
            'updated': updated_count,
            'skipped': skipped,
            'total_requested': len(course_ids)
        }
    
    @classmethod
    def get_upcoming_expiry(cls, days_ahead=7):
        """
        Get courses that will expire in the specified number of days
        
        Args:
            days_ahead (int): Number of days to look ahead
            
        Returns:
            QuerySet: Courses expiring soon
        """
        from datetime import timedelta
        
        future_date = timezone.now().date() + timedelta(days=days_ahead)
        today = timezone.now().date()
        
        return Course.objects.filter(
            status='published',
            end_date__gte=today,
            end_date__lte=future_date
        ) | Course.objects.filter(
            status='published',
            end_date__isnull=True,
            start_date__gte=today,
            start_date__lte=future_date
        )
