"""
Bulk Notification Progress Service
Handles progress tracking for bulk email operations
"""
import uuid
import json
from django.core.cache import cache
from django.utils import timezone
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class BulkNotificationProgress:
    """
    Service to track progress of bulk notification operations
    """

    CACHE_TIMEOUT = 300  # 5 minutes

    @classmethod
    def create_task(cls, total_emails: int, notification_type: str = 'email') -> str:
        """
        Create a new progress tracking task

        Args:
            total_emails: Total number of emails to send
            notification_type: Type of notification ('email', 'sms', 'both')

        Returns:
            task_id: Unique task identifier
        """
        task_id = str(uuid.uuid4())

        progress_data = {
            'task_id': task_id,
            'status': 'created',
            'total_emails': total_emails,
            'processed_emails': 0,
            'sent_emails': 0,
            'failed_emails': 0,
            'current_batch': 0,
            'total_batches': 0,
            'percentage': 0,
            'notification_type': notification_type,
            'created_at': timezone.now().isoformat(),
            'updated_at': timezone.now().isoformat(),
            'error_message': None
        }

        cache_key = cls._get_cache_key(task_id)
        cache.set(cache_key, progress_data, timeout=cls.CACHE_TIMEOUT)

        logger.info(f"Created progress task {task_id} for {total_emails} emails")
        return task_id

    @classmethod
    def update_progress(cls, task_id: str, processed: int, total: int, stats: Dict[str, int],
                       status: str, percentage: int = None, current_batch: int = None,
                       total_batches: int = None) -> bool:
        """
        Update progress for a task

        Args:
            task_id: Task identifier
            processed: Number of emails processed so far
            total: Total number of emails
            stats: Current statistics (sent, failed, etc.)
            status: Current status ('starting', 'sending', 'completed', 'failed')
            percentage: Progress percentage (0-100)
            current_batch: Current batch number
            total_batches: Total number of batches

        Returns:
            bool: True if update successful, False otherwise
        """
        try:
            cache_key = cls._get_cache_key(task_id)
            progress_data = cache.get(cache_key)

            if not progress_data:
                logger.warning(f"Progress task {task_id} not found in cache")
                return False

            # Update progress data
            progress_data.update({
                'status': status,
                'processed_emails': processed,
                'sent_emails': stats.get('sent', 0),
                'failed_emails': stats.get('failed', 0),
                'percentage': percentage or int((processed / total) * 100) if total > 0 else 0,
                'updated_at': timezone.now().isoformat(),
            })

            if current_batch is not None:
                progress_data['current_batch'] = current_batch
            if total_batches is not None:
                progress_data['total_batches'] = total_batches

            # Save updated data
            cache.set(cache_key, progress_data, timeout=cls.CACHE_TIMEOUT)

            logger.debug(f"Updated progress for task {task_id}: {percentage}% ({processed}/{total})")
            return True

        except Exception as e:
            logger.error(f"Failed to update progress for task {task_id}: {e}")
            return False

    @classmethod
    def get_progress(cls, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get current progress for a task

        Args:
            task_id: Task identifier

        Returns:
            dict: Progress data or None if not found
        """
        try:
            cache_key = cls._get_cache_key(task_id)
            progress_data = cache.get(cache_key)

            if not progress_data:
                logger.warning(f"Progress task {task_id} not found")
                return None

            return progress_data

        except Exception as e:
            logger.error(f"Failed to get progress for task {task_id}: {e}")
            return None

    @classmethod
    def mark_completed(cls, task_id: str, final_stats: Dict[str, int]) -> bool:
        """
        Mark task as completed with final statistics

        Args:
            task_id: Task identifier
            final_stats: Final sending statistics

        Returns:
            bool: True if successful, False otherwise
        """
        return cls.update_progress(
            task_id=task_id,
            processed=final_stats.get('sent', 0) + final_stats.get('failed', 0),
            total=final_stats.get('sent', 0) + final_stats.get('failed', 0),
            stats=final_stats,
            status='completed',
            percentage=100
        )

    @classmethod
    def mark_failed(cls, task_id: str, error_message: str) -> bool:
        """
        Mark task as failed with error message

        Args:
            task_id: Task identifier
            error_message: Error description

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            cache_key = cls._get_cache_key(task_id)
            progress_data = cache.get(cache_key)

            if not progress_data:
                return False

            progress_data.update({
                'status': 'failed',
                'error_message': error_message,
                'updated_at': timezone.now().isoformat(),
            })

            cache.set(cache_key, progress_data, timeout=cls.CACHE_TIMEOUT)
            logger.error(f"Marked task {task_id} as failed: {error_message}")
            return True

        except Exception as e:
            logger.error(f"Failed to mark task {task_id} as failed: {e}")
            return False

    @classmethod
    def cleanup_task(cls, task_id: str) -> bool:
        """
        Remove task data from cache

        Args:
            task_id: Task identifier

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            cache_key = cls._get_cache_key(task_id)
            cache.delete(cache_key)
            logger.info(f"Cleaned up progress task {task_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to cleanup task {task_id}: {e}")
            return False

    @classmethod
    def _get_cache_key(cls, task_id: str) -> str:
        """Get cache key for task ID"""
        return f"bulk_notification_progress_{task_id}"


def create_progress_callback(task_id: str):
    """
    Create a progress callback function for BatchEmailService

    Args:
        task_id: Task identifier

    Returns:
        function: Callback function that updates progress
    """
    def progress_callback(processed, total, stats, status, percentage=None, current_batch=None, total_batches=None):
        BulkNotificationProgress.update_progress(
            task_id=task_id,
            processed=processed,
            total=total,
            stats=stats,
            status=status,
            percentage=percentage,
            current_batch=current_batch,
            total_batches=total_batches
        )

    return progress_callback