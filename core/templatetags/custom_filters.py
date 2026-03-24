from django import template
from django.urls import reverse
from datetime import date
from core.services.staff_timesheet_service import StaffTimesheetService
from core.utils.url_utils import build_absolute_url

register = template.Library()

@register.filter
def format_duration(hours):
    """
    Format duration in hours to human-readable format
    """
    return StaffTimesheetService.format_duration(hours)

@register.filter
def classes_display(classes):
    """
    Format classes for display
    """
    return StaffTimesheetService.get_classes_display(classes)

@register.filter
def calculate_age(birth_date):
    """
    Calculate age from birth date
    Usage: {{ student.birth_date|calculate_age }}
    Returns age as integer or empty string if birth_date is None
    """
    if not birth_date:
        return ""

    today = date.today()
    age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
    return age

@register.simple_tag
def site_url(url_name, *args, **kwargs):
    """
    Generate absolute URL using the configured EduPulse application domain
    Usage: {% site_url 'enrollment:public_enrollment' %}
    """
    relative_url = reverse(url_name, args=args, kwargs=kwargs)
    return build_absolute_url(relative_url, app_domain=True)

@register.simple_tag
def enrollment_url(course_id=None):
    """
    Generate public enrollment URL with optional course parameter
    Usage: {% enrollment_url course.pk %}
    """
    base_url = build_absolute_url(reverse('enrollment:public_enrollment'), app_domain=True)
    if course_id:
        return f"{base_url}?course={course_id}"
    return base_url
