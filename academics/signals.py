"""
Django signals for automatic WooCommerce synchronization
"""
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.contrib.sites.models import Site
from .models import Course
from core.woocommerce_api import WooCommerceSyncService
import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Course)
def sync_course_to_woocommerce(sender, instance, created, **kwargs):
    """
    Automatically sync course to WooCommerce when saved
    Only sync published courses
    """
    try:
        # Only sync published courses to avoid draft products in WooCommerce
        if instance.status == 'published':
            sync_service = WooCommerceSyncService()
            result = sync_service.sync_course_to_woocommerce(instance)
            
            if result['status'] == 'success':
                action = 'created' if created else 'updated'
                logger.info(f"Successfully {action} WooCommerce product for course: {instance.name}")
            else:
                logger.error(f"Failed to sync course to WooCommerce: {result.get('message')}")
        else:
            # If course is not published but has external_id, sync status to WooCommerce (don't delete)
            if instance.external_id:
                sync_service = WooCommerceSyncService()
                result = sync_service.sync_course_to_woocommerce(instance)
                if result['status'] == 'success':
                    logger.info(f"Updated WooCommerce product status to draft for course: {instance.name}")
                else:
                    logger.error(f"Failed to update WooCommerce product status: {result.get('message')}")
                    
    except Exception as e:
        logger.error(f"Error in course WooCommerce sync signal: {str(e)}")


@receiver(post_delete, sender=Course)
def remove_course_from_woocommerce(sender, instance, **kwargs):
    """
    Remove course product from WooCommerce when course is deleted
    """
    try:
        if instance.external_id:
            sync_service = WooCommerceSyncService()
            result = sync_service.remove_course_from_woocommerce(instance)
            
            if result['status'] == 'success':
                logger.info(f"Successfully removed WooCommerce product for deleted course: {instance.name}")
            else:
                logger.error(f"Failed to remove course from WooCommerce: {result.get('message')}")
                
    except Exception as e:
        logger.error(f"Error in course WooCommerce deletion signal: {str(e)}")