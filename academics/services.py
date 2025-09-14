"""
Course Status Management Service

Centralized service for managing course status updates and consistency checks.
"""

from django.utils import timezone
from django.db.models import Q
from academics.models import Course
import logging

logger = logging.getLogger(__name__)


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