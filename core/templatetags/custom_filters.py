from django import template
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