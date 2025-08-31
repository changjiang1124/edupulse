from django import forms
from django.forms.widgets import Select
from django.core.exceptions import ValidationError


class DurationWidget(forms.MultiWidget):
    """
    Custom widget for duration input with hours and minutes (10-minute steps)
    """
    def __init__(self, attrs=None):
        # Hours: 0-12 hours
        hours_choices = [(i, f'{i} hour{"s" if i != 1 else ""}') for i in range(0, 13)]
        
        # Minutes: 0, 10, 20, 30, 40, 50 minutes
        minutes_choices = [(i, f'{i} min{"s" if i != 1 else ""}') for i in range(0, 60, 10)]
        
        widgets = [
            Select(choices=hours_choices, attrs={'class': 'form-select form-select-sm'}),
            Select(choices=minutes_choices, attrs={'class': 'form-select form-select-sm'}),
        ]
        super().__init__(widgets, attrs)

    def decompress(self, value):
        """
        Convert total minutes to hours and minutes
        """
        if value:
            hours = value // 60
            minutes = value % 60
            # Round minutes down to nearest 10-minute step to avoid inflation
            minutes = (minutes // 10) * 10
            return [hours, minutes]
        return [0, 0]

    def format_output(self, rendered_widgets):
        """
        Format the output HTML with improved layout
        """
        return f"""
        <div class="duration-field-container">
            <div class="row g-2">
                <div class="col-6">
                    <label class="form-label small text-muted mb-1">Hours</label>
                    {rendered_widgets[0]}
                </div>
                <div class="col-6">
                    <label class="form-label small text-muted mb-1">Minutes</label>
                    {rendered_widgets[1]}
                </div>
            </div>
        </div>
        """


class DurationField(forms.MultiValueField):
    """
    Custom field for duration input
    """
    widget = DurationWidget
    
    def __init__(self, *args, **kwargs):
        fields = [
            forms.IntegerField(min_value=0, max_value=12),  # Hours
            forms.IntegerField(min_value=0, max_value=50),  # Minutes (0-50 in 10-min steps)
        ]
        super().__init__(fields, *args, **kwargs)
    
    def compress(self, data_list):
        """
        Convert hours and minutes to total minutes
        """
        if data_list:
            hours = data_list[0] or 0
            minutes = data_list[1] or 0
            total_minutes = hours * 60 + minutes
            
            # Validate minimum duration
            if total_minutes < 10:
                raise ValidationError('Duration must be at least 10 minutes.')
            
            return total_minutes
        return 0