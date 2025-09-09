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
    
    def _generate_enhanced_description(self, course_data: Dict[str, Any]) -> str:
        """
        Generate enhanced product description with essential user information
        """
        from datetime import datetime
        
        # Start with basic description
        description = course_data.get('description', '')
        
        # Add essential course information
        info_sections = []
        
        # Course details section
        course_details = []
        
        # Price information with GST details
        price = course_data.get('price', 0)
        registration_fee = course_data.get('registration_fee')
        
        # Use price_display if available (includes GST label)
        if course_data.get('price_display'):
            price_display = course_data['price_display']
        else:
            price_display = f"${price}"
            if course_data.get('gst_info', {}).get('includes_gst'):
                price_display += " (inc GST)"
            else:
                price_display += " (ex GST)"
        
        if registration_fee and registration_fee > 0:
            reg_fee_display = f"${registration_fee}"
            if course_data.get('gst_info', {}).get('includes_gst'):
                reg_fee_display += " (inc GST)"
            else:
                reg_fee_display += " (ex GST)"
            
            total_fee = float(price) + float(registration_fee)
            total_display = f"${total_fee}"
            if course_data.get('gst_info', {}).get('includes_gst'):
                total_display += " (inc GST)"
            else:
                total_display += " (ex GST)"
            
            course_details.append(f"<strong>Course Fee:</strong> {price_display}")
            course_details.append(f"<strong>Registration Fee:</strong> {reg_fee_display} (for new students)")
            course_details.append(f"<strong>Total for New Students:</strong> {total_display}")
        else:
            course_details.append(f"<strong>Course Fee:</strong> {price_display}")
        
        # Add GST information note if available
        if course_data.get('gst_info'):
            gst_info = course_data['gst_info']
            gst_note = "<em>Note: All prices are displayed "
            if gst_info['includes_gst']:
                gst_note += f"inclusive of {gst_info['label']} ({gst_info['rate']*100:.0f}%)."
            else:
                gst_note += f"exclusive of {gst_info['label']} ({gst_info['rate']*100:.0f}%), which will be added at checkout."
            gst_note += "</em>"
            course_details.append(gst_note)
        
        # Vacancy information
        vacancy = course_data.get('vacancy')
        if vacancy:
            course_details.append(f"<strong>Available Places:</strong> {vacancy}")
        
        # Enrollment deadline
        enrollment_deadline = course_data.get('enrollment_deadline')
        if enrollment_deadline:
            try:
                if isinstance(enrollment_deadline, str):
                    deadline_date = datetime.fromisoformat(enrollment_deadline.replace('Z', '+00:00'))
                else:
                    deadline_date = enrollment_deadline
                formatted_deadline = deadline_date.strftime('%d %B %Y')
                course_details.append(f"<strong>Enrollment Deadline:</strong> {formatted_deadline}")
            except:
                course_details.append(f"<strong>Enrollment Deadline:</strong> {enrollment_deadline}")
        
        # Course dates
        start_date = course_data.get('start_date')
        end_date = course_data.get('end_date')
        if start_date:
            try:
                if isinstance(start_date, str):
                    start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                else:
                    start_dt = start_date
                formatted_start = start_dt.strftime('%d %B %Y')
                
                if end_date and end_date != start_date:
                    try:
                        if isinstance(end_date, str):
                            end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                        else:
                            end_dt = end_date
                        formatted_end = end_dt.strftime('%d %B %Y')
                        course_details.append(f"<strong>Course Period:</strong> {formatted_start} - {formatted_end}")
                    except:
                        course_details.append(f"<strong>Start Date:</strong> {formatted_start}")
                else:
                    course_details.append(f"<strong>Course Date:</strong> {formatted_start}")
            except:
                course_details.append(f"<strong>Start Date:</strong> {start_date}")
        
        # Course timing
        start_time = course_data.get('start_time')
        duration_minutes = course_data.get('duration_minutes')
        if start_time:
            try:
                if isinstance(start_time, str):
                    time_parts = start_time.split(':')
                    hour = int(time_parts[0])
                    minute = int(time_parts[1])
                    formatted_time = f"{hour:02d}:{minute:02d}"
                else:
                    formatted_time = start_time.strftime('%H:%M')
                
                timing_info = f"<strong>Class Time:</strong> {formatted_time}"
                if duration_minutes:
                    hours = duration_minutes // 60
                    mins = duration_minutes % 60
                    if hours > 0 and mins > 0:
                        duration_str = f"{hours}h {mins}min"
                    elif hours > 0:
                        duration_str = f"{hours} hour{'s' if hours > 1 else ''}"
                    else:
                        duration_str = f"{mins} minutes"
                    timing_info += f" ({duration_str})"
                
                course_details.append(timing_info)
            except:
                course_details.append(f"<strong>Class Time:</strong> {start_time}")
        
        # Facility/Location
        facility_name = course_data.get('facility_name')
        facility_address = course_data.get('facility_address')
        if facility_name:
            location_info = f"<strong>Location:</strong> {facility_name}"
            if facility_address:
                location_info += f" - {facility_address}"
            course_details.append(location_info)
        
        if course_details:
            info_sections.append(f"<h3>Course Information</h3>\n<ul>\n" + 
                               "\n".join(f"<li>{detail}</li>" for detail in course_details) + 
                               "\n</ul>")
        
        # Enrollment information
        enrollment_info = [
            "<strong>How to Enroll:</strong> Click 'Enrol Now' to complete your enrollment",
            "<strong>Payment:</strong> Bank transfer details will be provided after enrollment",
            "<strong>Questions?</strong> Contact us for more information"
        ]
        
        info_sections.append(f"<h3>Enrollment Details</h3>\n<ul>\n" + 
                           "\n".join(f"<li>{info}</li>" for info in enrollment_info) + 
                           "\n</ul>")
        
        # Combine original description with enhanced information
        enhanced_description = description
        if info_sections:
            enhanced_description += "\n\n" + "\n\n".join(info_sections)
        
        return enhanced_description
    
    def check_product_exists(self, wc_product_id: int) -> bool:
        """
        Check if a WooCommerce product exists by ID
        """
        try:
            result = self._make_request('GET', f'products/{wc_product_id}')
            return result is not None and 'id' in result
        except Exception as e:
            logger.warning(f"Product {wc_product_id} does not exist or is not accessible: {str(e)}")
            return False
    
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
        
        # Map EduPulse status to WooCommerce status
        wc_status = 'draft'  # Default to draft for safety
        if course_data.get('status') == 'published':
            wc_status = 'publish'
        elif course_data.get('status') in ['draft', 'expired']:
            wc_status = 'draft'
        
        logger.info(f"Mapping course status '{course_data.get('status')}' to WooCommerce status '{wc_status}'")
        
        product_data = {
            'name': course_data['name'],
            'type': 'external',  # External/Affiliate product type
            'status': wc_status,
            'featured': False,
            'catalog_visibility': 'visible',
            'description': self._generate_enhanced_description(course_data),
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
        
        # Map EduPulse status to WooCommerce status
        wc_status = 'draft'  # Default to draft for safety
        if course_data.get('status') == 'published':
            wc_status = 'publish'
        elif course_data.get('status') in ['draft', 'expired']:
            wc_status = 'draft'
        
        logger.info(f"Updating course status '{course_data.get('status')}' to WooCommerce status '{wc_status}' for product {wc_product_id}")
        
        product_data = {
            'name': course_data['name'],
            'status': wc_status,
            'description': self._generate_enhanced_description(course_data),
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
            
            # Get GST configuration for price display
            from core.models import OrganisationSettings
            org_settings = OrganisationSettings.get_instance()
            gst_config = OrganisationSettings.get_gst_config()
            
            # Format price with GST label for WooCommerce
            price_display = f"${course.price:.2f}"
            if org_settings.prices_include_gst:
                price_display += " (inc GST)"
            else:
                price_display += " (ex GST)"
            
            course_data = {
                'course_id': course.id,
                'name': course.name,
                'description': course.description or '',
                'short_description': course.short_description or '',
                'price': float(course.price),
                'price_display': price_display,
                'gst_info': {
                    'includes_gst': gst_config['includes_gst'],
                    'rate': float(gst_config['rate']),
                    'label': gst_config['label']
                },
                'registration_fee': float(course.registration_fee) if course.registration_fee else None,
                'vacancy': course.vacancy,
                'enrollment_deadline': course.enrollment_deadline.isoformat() if course.enrollment_deadline else None,
                'start_date': course.start_date.isoformat() if course.start_date else None,
                'end_date': course.end_date.isoformat() if course.end_date else None,
                'start_time': course.start_time.isoformat() if course.start_time else None,
                'duration_minutes': course.duration_minutes,
                'facility_name': course.facility.name if course.facility else None,
                'facility_address': course.facility.address if course.facility else None,
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
            
            # Check if course already has WooCommerce product ID
            if course.external_id:
                # First, try to update existing product
                wc_product_id = int(course.external_id)
                logger.info(f"Attempting to update existing WooCommerce product {wc_product_id} for course {course.id}")
                
                # Check if product exists first, then update or create
                product_exists = self.api.check_product_exists(wc_product_id)
                
                if product_exists:
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
                    # Product doesn't exist, create new one and update external_id
                    logger.warning(f"WooCommerce product {wc_product_id} not found for course {course.id}, creating new product")
                    result = self.api.create_external_product(course_data)
                    if result['status'] == 'success':
                        # Update with new WooCommerce product ID
                        new_wc_product_id = result['wc_product_id']
                        course.external_id = str(new_wc_product_id)
                        course.save(update_fields=['external_id'])
                        logger.info(f"Successfully created new WooCommerce product {new_wc_product_id} for course {course.id}")
                        success_result = result
                    else:
                        logger.error(f"Failed to create WooCommerce product for course {course.id}: {result.get('message')}")
                        success_result = result
            else:
                # Create new product
                logger.info(f"Creating new WooCommerce product for course {course.id}")
                result = self.api.create_external_product(course_data)
                if result['status'] == 'success':
                    # Save WooCommerce product ID to course
                    wc_product_id = result['wc_product_id']
                    course.external_id = str(wc_product_id)
                    course.save(update_fields=['external_id'])
                    logger.info(f"Successfully created WooCommerce product {wc_product_id} for course {course.id}")
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