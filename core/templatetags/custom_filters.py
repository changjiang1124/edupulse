from django import template
from django.conf import settings
from django.urls import reverse
from core.services.staff_timesheet_service import StaffTimesheetService

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

@register.simple_tag
def site_url(url_name, *args, **kwargs):
    """
    Generate absolute URL using configured site domain
    Usage: {% site_url 'enrollment:public_enrollment' %}
    """
    relative_url = reverse(url_name, args=args, kwargs=kwargs)
    return f"{settings.SITE_PROTOCOL}://{settings.SITE_DOMAIN}{relative_url}"

@register.simple_tag
def enrollment_url(course_id=None):
    """
    Generate public enrollment URL with optional course parameter
    Usage: {% enrollment_url course.pk %}
    """
    base_url = f"{settings.SITE_PROTOCOL}://{settings.SITE_DOMAIN}{reverse('enrollment:public_enrollment')}"
    if course_id:
        return f"{base_url}?course={course_id}"
    return base_url