"""
Template tags for price display with GST handling
"""
from django import template
from decimal import Decimal
from core.models import OrganisationSettings

register = template.Library()


@register.simple_tag
def format_price(amount, show_gst_label=True, show_breakdown=False):
    """
    Format price with GST label based on organisation settings
    Usage: {% format_price course.price %}
    """
    if not amount:
        return "$0.00"
    
    settings = OrganisationSettings.get_instance()
    formatted_price = f"${amount:,.2f}"
    
    if show_gst_label:
        gst_label = " (inc GST)" if settings.prices_include_gst else " (ex GST)"
        formatted_price += gst_label
    
    return formatted_price


@register.simple_tag
def gst_config():
    """
    Get GST configuration for templates
    Usage: {% gst_config as gst_settings %}
    """
    return OrganisationSettings.get_gst_config()


@register.inclusion_tag('core/tags/price_breakdown.html')
def price_breakdown(course, show_details=False, show_registration_fee=True):
    """
    Display price breakdown with GST details
    Usage: {% price_breakdown course show_details=True %}
    """
    breakdown = course.get_price_breakdown()
    settings = OrganisationSettings.get_instance()
    
    context = {
        'course': course,
        'breakdown': breakdown,
        'settings': settings,
        'show_details': show_details,
        'show_registration_fee': show_registration_fee
    }
    
    # Add registration fee breakdown if exists
    if show_registration_fee and course.registration_fee:
        context['reg_breakdown'] = course.get_registration_fee_breakdown()
        context['total_breakdown'] = course.get_total_course_fee_breakdown()
    
    return context


@register.inclusion_tag('core/tags/enrollment_fee_breakdown.html')
def enrollment_fee_breakdown(enrollment, show_details=True):
    """
    Display enrollment fee breakdown with GST details
    Usage: {% enrollment_fee_breakdown enrollment %}
    """
    settings = OrganisationSettings.get_instance()
    course_breakdown = enrollment.course.get_price_breakdown()
    
    context = {
        'enrollment': enrollment,
        'course_breakdown': course_breakdown,
        'settings': settings,
        'show_details': show_details,
        'total_fee': enrollment.get_total_fee(),
        'outstanding_fee': enrollment.get_outstanding_fee()
    }
    
    # Add registration fee breakdown if exists
    if enrollment.course.registration_fee:
        context['reg_breakdown'] = enrollment.course.get_registration_fee_breakdown()
        context['total_breakdown'] = enrollment.course.get_total_course_fee_breakdown()
    
    return context


@register.filter
def currency(value):
    """
    Format value as currency
    Usage: {{ amount|currency }}
    """
    if not value:
        return "$0.00"
    return f"${value:,.2f}"


@register.filter
def percentage(value):
    """
    Format decimal as percentage
    Usage: {{ 0.10|percentage }}
    """
    if not value:
        return "0%"
    return f"{float(value) * 100:.1f}%"


@register.simple_tag
def gst_amount_from_price(price, include_gst=None):
    """
    Calculate GST amount from price based on settings
    Usage: {% gst_amount_from_price course.price %}
    """
    if not price:
        return Decimal('0.00')
    
    settings = OrganisationSettings.get_instance()
    includes_gst = include_gst if include_gst is not None else settings.prices_include_gst
    
    if includes_gst:
        # Price includes GST - extract GST amount
        gst_amount = price / (1 + settings.gst_rate) * settings.gst_rate
    else:
        # Price excludes GST - calculate GST amount
        gst_amount = price * settings.gst_rate
    
    return gst_amount.quantize(Decimal('0.01'))


@register.simple_tag
def price_with_gst_label(price, show_label=True):
    """
    Display price with appropriate GST label
    Usage: {% price_with_gst_label course.price %}
    """
    if not price:
        return "$0.00"
    
    formatted = f"${price:,.2f}"
    
    if show_label:
        settings = OrganisationSettings.get_instance()
        label = " (inc GST)" if settings.prices_include_gst else " (ex GST)"
        formatted += label
    
    return formatted