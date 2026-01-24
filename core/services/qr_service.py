"""
QR Code Service for EduPulse Teacher Attendance System
Handles QR code generation and validation for teacher check-ins
"""
import qrcode
import qrcode.image.svg
import base64
import io
import json
import hashlib
import secrets
from datetime import datetime, timedelta
from django.conf import settings
from django.utils import timezone
from django.urls import reverse
from django.contrib.sites.models import Site
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class QRCodeService:
    """
    Service for generating and validating QR codes for teacher attendance
    """
    
    @staticmethod
    def generate_attendance_qr_code(facility, class_instance=None, expires_minutes=60):
        """
        Generate QR code for teacher attendance at a specific facility
        
        Args:
            facility: Facility object where attendance will be recorded
            class_instance: Optional specific class instance
            expires_minutes: QR code expiration time in minutes
            
        Returns:
            Dictionary with QR code data and image
        """
        try:
            # Create secure token for this QR code
            token = secrets.token_urlsafe(32)
            
            # Calculate expiration time
            expires_at = timezone.now() + timedelta(minutes=expires_minutes)
            
            # Create QR code data
            qr_data = {
                'facility_id': facility.id,
                'facility_name': facility.name,
                'class_id': class_instance.id if class_instance else None,
                'token': token,
                'expires_at': expires_at.isoformat(),
                'generated_at': timezone.now().isoformat()
            }
            
            # Get current site domain
            site = Site.objects.get_current()
            
            # Create attendance URL with encoded data
            encoded_data = base64.urlsafe_b64encode(
                json.dumps(qr_data).encode('utf-8')
            ).decode('utf-8')
            
            attendance_url = f"https://{site.domain}{reverse('teacher_qr_attendance')}?data={encoded_data}"
            
            # Generate QR code
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(attendance_url)
            qr.make(fit=True)
            
            # Create QR code image
            img = qr.make_image(fill_color="black", back_color="white")
            
            # Convert to base64 for easy embedding
            buffer = io.BytesIO()
            img.save(buffer, format='PNG')
            img_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
            
            # Store QR code data in cache/database for validation
            QRCodeService._store_qr_token(token, qr_data)
            
            return {
                'success': True,
                'qr_code_image': img_base64,
                'attendance_url': attendance_url,
                'token': token,
                'expires_at': expires_at,
                'facility': facility,
                'class_instance': class_instance,
                'qr_data': qr_data
            }
            
        except Exception as e:
            logger.error(f"Error generating QR code for facility {facility.id}: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    @staticmethod
    def validate_qr_code(data_string):
        """
        Validate QR code data and return facility information
        
        Args:
            data_string: Base64 encoded QR code data
            
        Returns:
            Dictionary with validation results and facility data
        """
        try:
            # Decode the QR code data
            decoded_data = base64.urlsafe_b64decode(data_string.encode('utf-8'))
            qr_data = json.loads(decoded_data.decode('utf-8'))
            
            # Check if QR code has expired
            expires_at = datetime.fromisoformat(qr_data['expires_at'].replace('Z', '+00:00'))
            if timezone.now() > expires_at:
                return {
                    'valid': False,
                    'error': 'QR code has expired',
                    'expired': True
                }
            
            # Validate token
            token = qr_data.get('token')
            if not QRCodeService._validate_qr_token(token, qr_data):
                return {
                    'valid': False,
                    'error': 'Invalid or expired QR code token'
                }
            
            # Get facility
            from facilities.models import Facility
            try:
                facility = Facility.objects.get(id=qr_data['facility_id'], is_active=True)
            except Facility.DoesNotExist:
                return {
                    'valid': False,
                    'error': 'Facility not found or inactive'
                }
            
            # Get class instance if specified
            class_instance = None
            if qr_data.get('class_id'):
                from academics.models import Class
                try:
                    class_instance = Class.objects.get(id=qr_data['class_id'], is_active=True)
                except Class.DoesNotExist:
                    logger.warning(f"Class {qr_data['class_id']} not found for QR code")
                    # Don't fail validation if class not found, allow general facility check-in
            
            return {
                'valid': True,
                'facility': facility,
                'class_instance': class_instance,
                'qr_data': qr_data,
                'token': token
            }
            
        except Exception as e:
            logger.error(f"Error validating QR code: {str(e)}")
            return {
                'valid': False,
                'error': f'Invalid QR code format: {str(e)}'
            }
    
    @staticmethod
    def generate_facility_qr_codes(facility, days_ahead=7):
        """
        Generate QR codes for a facility for upcoming classes
        
        Args:
            facility: Facility object
            days_ahead: Number of days ahead to generate QR codes for
            
        Returns:
            List of QR code data for upcoming classes
        """
        from academics.models import Class
        from datetime import date
        
        try:
            # Get classes for this facility in the next week
            start_date = timezone.now().date()
            end_date = start_date + timedelta(days=days_ahead)
            
            classes = Class.objects.filter(
                facility=facility,
                date__gte=start_date,
                date__lte=end_date,
                is_active=True
            ).order_by('date', 'start_time')
            
            qr_codes = []
            
            # Generate general facility QR code
            general_qr = QRCodeService.generate_attendance_qr_code(
                facility=facility,
                expires_minutes=24*60  # 24 hours
            )
            if general_qr['success']:
                general_qr['type'] = 'general'
                general_qr['title'] = f"General Check-in - {facility.name}"
                qr_codes.append(general_qr)
            
            # Generate specific QR codes for each class
            for class_instance in classes:
                class_qr = QRCodeService.generate_attendance_qr_code(
                    facility=facility,
                    class_instance=class_instance,
                    expires_minutes=4*60  # 4 hours
                )
                if class_qr['success']:
                    class_qr['type'] = 'class_specific'
                    class_qr['title'] = f"{class_instance.course.name} - {class_instance.date.strftime('%m/%d')} {class_instance.start_time.strftime('%H:%M')}"
                    qr_codes.append(class_qr)
            
            return {
                'success': True,
                'facility': facility,
                'qr_codes': qr_codes,
                'total_generated': len(qr_codes)
            }
            
        except Exception as e:
            logger.error(f"Error generating QR codes for facility {facility.id}: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    @staticmethod
    def _store_qr_token(token, qr_data):
        """
        Store QR code token for validation (using Django cache)
        """
        from django.core.cache import cache
        
        # Store for the duration of QR code validity plus buffer
        expires_at = datetime.fromisoformat(qr_data['expires_at'].replace('Z', '+00:00'))
        timeout = int((expires_at - timezone.now()).total_seconds()) + 300  # 5 min buffer
        
        cache_key = f"qr_token_{token}"
        cache.set(cache_key, qr_data, timeout=max(timeout, 60))  # Minimum 1 minute
        
    @staticmethod
    def _validate_qr_token(token, qr_data):
        """
        Validate QR code token against stored data
        """
        from django.core.cache import cache
        
        cache_key = f"qr_token_{token}"
        cached_data = cache.get(cache_key)
        
        if not cached_data:
            return False
        
        # Verify key data matches
        return (
            cached_data.get('facility_id') == qr_data.get('facility_id') and
            cached_data.get('generated_at') == qr_data.get('generated_at') and
            cached_data.get('token') == qr_data.get('token')
        )
    
    @staticmethod
    def invalidate_qr_token(token):
        """
        Invalidate a QR code token (useful after successful check-in)
        """
        from django.core.cache import cache
        
        cache_key = f"qr_token_{token}"
        cache.delete(cache_key)
    
    @staticmethod
    def generate_svg_qr_code(attendance_url):
        """
        Generate SVG QR code for better scalability
        """
        try:
            factory = qrcode.image.svg.SvgPathImage
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
                image_factory=factory
            )
            qr.add_data(attendance_url)
            qr.make(fit=True)
            
            img = qr.make_image()
            
            # Convert SVG to string
            svg_buffer = io.StringIO()
            img.save(svg_buffer)
            svg_string = svg_buffer.getvalue()
            
            return svg_string
            
        except Exception as e:
            logger.error(f"Error generating SVG QR code: {str(e)}")
            return None