"""
GPS utility functions for teacher attendance system
"""
import math
import requests
from decimal import Decimal
from django.conf import settings
from facilities.models import Facility
from typing import Optional, Tuple, List, Dict


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great circle distance between two points 
    on the earth (specified in decimal degrees) using the Haversine formula.
    
    Args:
        lat1, lon1: Latitude and longitude of point 1
        lat2, lon2: Latitude and longitude of point 2
        
    Returns:
        Distance in meters
    """
    # Convert decimal degrees to radians
    lat1_rad = math.radians(float(lat1))
    lon1_rad = math.radians(float(lon1))
    lat2_rad = math.radians(float(lat2))
    lon2_rad = math.radians(float(lon2))
    
    # Haversine formula
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    a = (math.sin(dlat / 2) ** 2 + 
         math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2)
    c = 2 * math.asin(math.sqrt(a))
    
    # Earth's radius in meters
    earth_radius = 6371000
    distance = earth_radius * c
    
    return distance


def find_nearest_facility(teacher_lat: float, teacher_lon: float) -> Optional[Dict]:
    """
    Find the nearest facility to the teacher's current location.
    
    Args:
        teacher_lat: Teacher's current latitude
        teacher_lon: Teacher's current longitude
        
    Returns:
        Dictionary with facility info and distance, or None if no suitable facility found
    """
    facilities = Facility.objects.filter(
        is_active=True,
        latitude__isnull=False,
        longitude__isnull=False
    )
    
    if not facilities.exists():
        return None
    
    nearest_facility = None
    min_distance = float('inf')
    
    for facility in facilities:
        distance = haversine_distance(
            teacher_lat, teacher_lon,
            float(facility.latitude), float(facility.longitude)
        )
        
        if distance < min_distance:
            min_distance = distance
            nearest_facility = facility
    
    if nearest_facility:
        return {
            'facility': nearest_facility,
            'distance': min_distance,
            'within_range': min_distance <= nearest_facility.attendance_radius
        }
    
    return None


def verify_teacher_location(teacher_lat: float, teacher_lon: float) -> Dict:
    """
    Verify if teacher's location is valid for attendance.
    
    Args:
        teacher_lat: Teacher's current latitude
        teacher_lon: Teacher's current longitude
        
    Returns:
        Dictionary with verification results
    """
    result = find_nearest_facility(teacher_lat, teacher_lon)
    
    if not result:
        return {
            'valid': False,
            'error': 'No facilities found with GPS coordinates',
            'facility': None,
            'distance': None
        }
    
    facility = result['facility']
    distance = result['distance']
    within_range = result['within_range']
    
    return {
        'valid': within_range,
        'facility': facility,
        'distance': distance,
        'within_range': within_range,
        'max_allowed_distance': facility.attendance_radius,
        'error': None if within_range else f'Too far from {facility.name}. Distance: {distance:.1f}m, Maximum allowed: {facility.attendance_radius}m'
    }


def get_today_classes_for_teacher_at_facility(teacher, facility, date=None):
    """
    Get today's classes for a teacher at a specific facility.
    
    Args:
        teacher: Staff instance (teacher)
        facility: Facility instance
        date: Date to check (defaults to today)
        
    Returns:
        QuerySet of Class objects
    """
    from django.utils import timezone
    from academics.models import Class
    
    if date is None:
        date = timezone.now().date()
    
    return Class.objects.filter(
        date=date,
        facility=facility,
        teacher=teacher,
        is_active=True
    ).select_related('course').order_by('start_time')


def geocode_address(address: str) -> Optional[Tuple[float, float]]:
    """
    Convert address to GPS coordinates using Google Geocoding API.
    
    Args:
        address: Street address to geocode
        
    Returns:
        Tuple of (latitude, longitude) or None if geocoding fails
    """
    api_key = getattr(settings, 'GOOGLE_MAPS_API_KEY', None)
    if not api_key:
        return None
    
    url = 'https://maps.googleapis.com/maps/api/geocode/json'
    params = {
        'address': address,
        'key': api_key
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if data['status'] == 'OK' and data['results']:
            location = data['results'][0]['geometry']['location']
            return (location['lat'], location['lng'])
    
    except (requests.RequestException, KeyError, IndexError):
        pass
    
    return None


def get_client_ip(request) -> str:
    """
    Extract client IP address from request.
    
    Args:
        request: Django request object
        
    Returns:
        IP address string
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def get_user_agent(request) -> str:
    """
    Extract user agent from request.
    
    Args:
        request: Django request object
        
    Returns:
        User agent string
    """
    return request.META.get('HTTP_USER_AGENT', '')