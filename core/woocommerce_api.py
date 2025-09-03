"""
WooCommerce API Integration for EduPulse
Handles synchronization of courses to WooCommerce as external products
"""
import os
import requests
import json
import logging
import time
from typing import Dict, Any, Optional
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


class WooCommerceAPI:
    """
    WooCommerce API client for course synchronization
    """
    
    def __init__(self):
        self.consumer_key = os.getenv('WC_CONSUMER_KEY')
        self.consumer_secret = os.getenv('WC_CONSUMER_SECRET')
        self.base_url = os.getenv('WC_BASE_URL')
        
        if not all([self.consumer_key, self.consumer_secret, self.base_url]):
            logger.error("Missing WooCommerce API credentials in environment variables")
            raise ValueError("WooCommerce API credentials not properly configured")
    
    def _get_auth(self):
        """Get basic authentication tuple"""
        return (self.consumer_key, self.consumer_secret)
    
    def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Make authenticated request to WooCommerce API
        """
        url = f"{self.base_url}/{endpoint}"
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'EduPulse/1.0.0'
        }
        
        try:
            if method.upper() == 'GET':
                response = requests.get(url, auth=self._get_auth(), headers=headers, timeout=30)
            elif method.upper() == 'POST':
                response = requests.post(url, auth=self._get_auth(), headers=headers, 
                                       json=data, timeout=30)
            elif method.upper() == 'PUT':
                response = requests.put(url, auth=self._get_auth(), headers=headers, 
                                      json=data, timeout=30)
            elif method.upper() == 'DELETE':
                response = requests.delete(url, auth=self._get_auth(), headers=headers, timeout=30)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"WooCommerce API request failed: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_data = e.response.json()
                    logger.error(f"WooCommerce API error details: {error_data}")
                except:
                    logger.error(f"WooCommerce API error response: {e.response.text}")
            raise
    
    def test_connection(self) -> Dict[str, Any]:
        """
        Test WooCommerce API connection
        """
        try:
            # Test with a simple system status check
            result = self._make_request('GET', 'system_status')
            logger.info("WooCommerce API connection successful")
            return {
                'status': 'success',
                'message': 'WooCommerce API connection successful',
                'data': result
            }
        except Exception as e:
            logger.error(f"WooCommerce API connection test failed: {str(e)}")
            return {
                'status': 'error',
                'message': f'WooCommerce API connection failed: {str(e)}',
                'data': None
            }
    
    def create_external_product(self, course_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create an external product in WooCommerce for a course
        External products redirect to external URL (EduPulse enrollment form)
        """
        # Prepare product images for WooCommerce
        images = []
        if course_data.get('featured_image_url'):
            images.append({
                'src': course_data['featured_image_url'],
                'alt': f"{course_data['name']} featured image"
            })
        
        product_data = {
            'name': course_data['name'],
            'type': 'external',  # External/Affiliate product type
            'status': 'publish' if course_data.get('status') == 'published' else 'draft',
            'featured': False,
            'catalog_visibility': 'visible',
            'description': course_data.get('description', ''),
            'short_description': course_data.get('short_description', ''),
            'regular_price': str(course_data.get('price', '0')),
            'external_url': course_data.get('enrollment_url', ''),
            'button_text': 'Enrol Now',  # Australian English
            'images': images,  # Add images to product data
            'meta_data': [
                {
                    'key': '_edupulse_course_id',
                    'value': str(course_data.get('course_id', ''))
                },
                {
                    'key': '_edupulse_sync_version',
                    'value': '1.0'
                }
            ],
            'categories': course_data.get('categories', []),
            'tags': course_data.get('tags', []),
        }
        
        try:
            result = self._make_request('POST', 'products', product_data)
            logger.info(f"Successfully created WooCommerce product: {result.get('id')}")
            return {
                'status': 'success',
                'wc_product_id': result.get('id'),
                'data': result
            }
        except Exception as e:
            logger.error(f"Failed to create WooCommerce product: {str(e)}")
            return {
                'status': 'error',
                'message': str(e),
                'data': None
            }
    
    def update_external_product(self, wc_product_id: int, course_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update an existing external product in WooCommerce
        """
        # Prepare product images for WooCommerce
        images = []
        if course_data.get('featured_image_url'):
            images.append({
                'src': course_data['featured_image_url'],
                'alt': f"{course_data['name']} featured image"
            })
        
        product_data = {
            'name': course_data['name'],
            'status': 'publish' if course_data.get('status') == 'published' else 'draft',
            'description': course_data.get('description', ''),
            'short_description': course_data.get('short_description', ''),
            'regular_price': str(course_data.get('price', '0')),
            'external_url': course_data.get('enrollment_url', ''),
            'button_text': 'Enrol Now',
            'images': images,  # Add images to product data
            'categories': course_data.get('categories', []),
            'tags': course_data.get('tags', []),
        }
        
        try:
            result = self._make_request('PUT', f'products/{wc_product_id}', product_data)
            logger.info(f"Successfully updated WooCommerce product: {wc_product_id}")
            return {
                'status': 'success',
                'data': result
            }
        except Exception as e:
            logger.error(f"Failed to update WooCommerce product {wc_product_id}: {str(e)}")
            return {
                'status': 'error',
                'message': str(e),
                'data': None
            }
    
    def delete_product(self, wc_product_id: int) -> Dict[str, Any]:
        """
        Delete a product in WooCommerce
        """
        try:
            result = self._make_request('DELETE', f'products/{wc_product_id}', {'force': True})
            logger.info(f"Successfully deleted WooCommerce product: {wc_product_id}")
            return {
                'status': 'success',
                'data': result
            }
        except Exception as e:
            logger.error(f"Failed to delete WooCommerce product {wc_product_id}: {str(e)}")
            return {
                'status': 'error',
                'message': str(e),
                'data': None
            }
    
    def get_product(self, wc_product_id: int) -> Dict[str, Any]:
        """
        Get a specific product from WooCommerce
        """
        try:
            result = self._make_request('GET', f'products/{wc_product_id}')
            return {
                'status': 'success',
                'data': result
            }
        except Exception as e:
            logger.error(f"Failed to get WooCommerce product {wc_product_id}: {str(e)}")
            return {
                'status': 'error',
                'message': str(e),
                'data': None
            }
    
    def list_products(self, per_page: int = 10, page: int = 1) -> Dict[str, Any]:
        """
        List products from WooCommerce
        """
        try:
            endpoint = f'products?per_page={per_page}&page={page}'
            result = self._make_request('GET', endpoint)
            return {
                'status': 'success',
                'data': result
            }
        except Exception as e:
            logger.error(f"Failed to list WooCommerce products: {str(e)}")
            return {
                'status': 'error',
                'message': str(e),
                'data': None
            }
    
    def get_or_create_category(self, category_name: str) -> Dict[str, Any]:
        """
        Get existing category or create new one in WooCommerce
        """
        try:
            # First, search for existing category
            categories_result = self._make_request('GET', f'products/categories?search={category_name}')
            
            for category in categories_result:
                if category['name'].lower() == category_name.lower():
                    return {
                        'status': 'success',
                        'category_id': category['id'],
                        'category': category
                    }
            
            # Category doesn't exist, create it
            category_data = {
                'name': category_name,
                'slug': category_name.lower().replace(' ', '-'),
                'description': f'Course category: {category_name}'
            }
            
            result = self._make_request('POST', 'products/categories', category_data)
            logger.info(f"Successfully created WooCommerce category: {category_name}")
            return {
                'status': 'success',
                'category_id': result['id'],
                'category': result
            }
            
        except Exception as e:
            logger.error(f"Failed to get/create WooCommerce category {category_name}: {str(e)}")
            return {
                'status': 'error',
                'message': str(e),
                'data': None
            }


class WooCommerceSyncService:
    """
    Service class to handle course synchronization with WooCommerce
    """
    
    def __init__(self):
        self.api = WooCommerceAPI()
    
    def sync_course_to_woocommerce(self, course, log_sync=True):
        """
        Sync a course to WooCommerce as external product with comprehensive logging
        """
        from django.urls import reverse
        from django.contrib.sites.models import Site
        from core.models import WooCommerceSyncLog
        
        # Create sync log entry
        sync_log = None
        start_time = time.time()
        
        if log_sync:
            sync_type = 'update' if course.external_id else 'create'
            sync_log = WooCommerceSyncLog.objects.create(
                course=course,
                sync_type=sync_type,
                status='processing',
                wc_product_id=course.external_id or '',
            )
        
        try:
            # Prepare course data for WooCommerce
            site = Site.objects.get_current()
            enrollment_url = f"https://{site.domain}{reverse('enrollment:public_enrollment')}?course={course.id}"
            
            # Handle featured image URL
            featured_image_url = None
            if course.featured_image:
                featured_image_url = f"https://{site.domain}{course.featured_image.url}"
            
            # Map category to WooCommerce category
            category_mapping = {
                'term_courses': 'Term Courses',
                'holiday_program': 'Holiday Program', 
                'day_courses': 'Day Courses'
            }
            category_name = category_mapping.get(course.category, 'Courses')
            
            # Get or create category in WooCommerce
            category_result = self.api.get_or_create_category(category_name)
            categories = []
            if category_result['status'] == 'success':
                categories = [{'id': category_result['category_id']}]
                # Log category info in sync log
                if sync_log:
                    sync_log.wc_category_id = str(category_result['category_id'])
                    sync_log.wc_category_name = category_name
            else:
                logger.warning(f"Failed to create/get category {category_name}, using default")
                categories = [{'name': category_name}]  # Fallback to name-based
            
            course_data = {
                'course_id': course.id,
                'name': course.name,
                'description': course.description or '',
                'short_description': course.short_description or '',
                'price': float(course.price),
                'status': course.status,
                'enrollment_url': enrollment_url,
                'featured_image_url': featured_image_url,  # Add image URL
                'categories': categories,
                'tags': [{'name': course.get_category_display()}]  # Add category as tag too
            }
            
            # Store request data in log
            if sync_log:
                sync_log.request_data = course_data
                sync_log.save()
            
            # Check if course already has WooCommerce product
            if course.external_id:
                # Update existing product
                wc_product_id = int(course.external_id)
                result = self.api.update_external_product(wc_product_id, course_data)
                if result['status'] == 'success':
                    logger.info(f"Successfully updated WooCommerce product for course {course.id}")
                    success_result = {
                        'status': 'success',
                        'wc_product_id': wc_product_id,
                        'data': result.get('data', {})
                    }
                else:
                    logger.error(f"Failed to update WooCommerce product for course {course.id}: {result.get('message')}")
                    success_result = result
            else:
                # Create new product
                result = self.api.create_external_product(course_data)
                if result['status'] == 'success':
                    # Save WooCommerce product ID to course
                    wc_product_id = result['wc_product_id']
                    course.external_id = str(wc_product_id)
                    course.save(update_fields=['external_id'])
                    logger.info(f"Successfully created WooCommerce product for course {course.id}")
                    success_result = result
                else:
                    logger.error(f"Failed to create WooCommerce product for course {course.id}: {result.get('message')}")
                    success_result = result
            
            # Update sync log with results
            if sync_log:
                end_time = time.time()
                duration_ms = int((end_time - start_time) * 1000)
                
                if success_result['status'] == 'success':
                    sync_log.status = 'success'
                    sync_log.wc_product_id = str(success_result.get('wc_product_id', course.external_id))
                    sync_log.response_data = success_result.get('data', {})
                    sync_log.completed_at = timezone.now()
                else:
                    sync_log.status = 'failed'
                    sync_log.error_message = success_result.get('message', 'Unknown error')
                    sync_log.response_data = success_result.get('data', {})
                
                sync_log.duration_ms = duration_ms
                sync_log.save()
            
            return success_result
                    
        except Exception as e:
            logger.error(f"Error syncing course {course.id} to WooCommerce: {str(e)}")
            
            # Update sync log with error
            if sync_log:
                end_time = time.time()
                duration_ms = int((end_time - start_time) * 1000)
                
                sync_log.status = 'failed'
                sync_log.error_message = str(e)
                sync_log.duration_ms = duration_ms
                sync_log.retry_count += 1
                sync_log.save()
            
            return {
                'status': 'error',
                'message': str(e),
                'data': None
            }
    
    def remove_course_from_woocommerce(self, course, log_sync=True):
        """
        Remove course product from WooCommerce with comprehensive logging
        """
        from core.models import WooCommerceSyncLog
        
        if not course.external_id:
            return {
                'status': 'success',
                'message': 'Course not synced to WooCommerce'
            }
        
        # Create sync log entry
        sync_log = None
        start_time = time.time()
        
        if log_sync:
            sync_log = WooCommerceSyncLog.objects.create(
                course=course,
                sync_type='delete',
                status='processing',
                wc_product_id=course.external_id,
            )
        
        try:
            wc_product_id = int(course.external_id)
            result = self.api.delete_product(wc_product_id)
            
            if result['status'] == 'success':
                # Clear external_id from course
                course.external_id = None
                course.save(update_fields=['external_id'])
                logger.info(f"Successfully removed WooCommerce product for course {course.id}")
            
            # Update sync log with results
            if sync_log:
                end_time = time.time()
                duration_ms = int((end_time - start_time) * 1000)
                
                if result['status'] == 'success':
                    sync_log.status = 'success'
                    sync_log.completed_at = timezone.now()
                else:
                    sync_log.status = 'failed'
                    sync_log.error_message = result.get('message', 'Unknown error')
                
                sync_log.response_data = result.get('data', {})
                sync_log.duration_ms = duration_ms
                sync_log.save()
            
            return result
            
        except Exception as e:
            logger.error(f"Error removing course {course.id} from WooCommerce: {str(e)}")
            
            # Update sync log with error
            if sync_log:
                end_time = time.time()
                duration_ms = int((end_time - start_time) * 1000)
                
                sync_log.status = 'failed'
                sync_log.error_message = str(e)
                sync_log.duration_ms = duration_ms
                sync_log.retry_count += 1
                sync_log.save()
            
            return {
                'status': 'error',
                'message': str(e),
                'data': None
            }
    
    def test_api_connection(self):
        """
        Test WooCommerce API connection
        """
        return self.api.test_connection()