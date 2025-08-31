from django import forms
from tinymce.widgets import TinyMCE
from .models import Course, Class
from .widgets import DurationField


class CourseForm(forms.ModelForm):
    """Course form with Bootstrap styling"""
    
    class Meta:
        model = Course
        fields = [
            'name', 'short_description', 'description', 'price', 'course_type', 'status', 'teacher',
            'start_date', 'end_date', 'repeat_pattern', 'repeat_weekday', 'repeat_day_of_month', 
            'start_time', 'duration_minutes', 'vacancy', 'facility', 'classroom', 'is_bookable',
            'enrollment_deadline'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter course name'
            }),
            'short_description': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Brief description for website listing',
                'maxlength': 500
            }),
            'description': TinyMCE(attrs={'cols': 80, 'rows': 30}),
            'price': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0'
            }),
            'course_type': forms.Select(attrs={
                'class': 'form-select'
            }),
            'status': forms.Select(attrs={
                'class': 'form-select'
            }),
            'teacher': forms.Select(attrs={
                'class': 'form-select'
            }),
            'start_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'end_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'repeat_pattern': forms.Select(attrs={
                'class': 'form-select'
            }),
            'repeat_weekday': forms.Select(attrs={
                'class': 'form-select'
            }),
            'repeat_day_of_month': forms.Select(attrs={
                'class': 'form-select'
            }),
            'start_time': forms.TimeInput(attrs={
                'class': 'form-control',
                'type': 'time'
            }),
            'duration_minutes': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '10',
                'step': '10',
                'placeholder': 'Duration in minutes (e.g. 60, 90, 120)'
            }),
            'vacancy': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1'
            }),
            'facility': forms.Select(attrs={
                'class': 'form-select'
            }),
            'classroom': forms.Select(attrs={
                'class': 'form-select'
            }),
            'is_bookable': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'enrollment_deadline': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
        }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Create day of month choices (1-31)
        day_choices = [('', 'Select day...')] + [(i, f'{i}') for i in range(1, 32)]
        self.fields['repeat_day_of_month'] = forms.ChoiceField(
            choices=day_choices,
            required=False,
            widget=forms.Select(attrs={'class': 'form-select'})
        )
        
    def clean_repeat_weekday(self):
        """Clean repeat_weekday field to convert empty string to None"""
        value = self.cleaned_data.get('repeat_weekday')
        return None if value == '' else value
        
    def clean_repeat_day_of_month(self):
        """Clean repeat_day_of_month field to convert empty string to None"""
        value = self.cleaned_data.get('repeat_day_of_month')
        return None if value == '' else value


class CourseUpdateForm(CourseForm):
    """Course update form with class update options"""
    
    class Meta(CourseForm.Meta):
        fields = CourseForm.Meta.fields + ['is_active', 'bookable_state']
        widgets = CourseForm.Meta.widgets.copy()
        widgets.update({
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'bookable_state': forms.Select(attrs={
                'class': 'form-select'
            })
        })
    
    # Additional fields for class update control
    update_existing_classes = forms.BooleanField(
        required=False,
        initial=True,
        label='Update Existing Classes',
        help_text='Apply changes to existing class sessions',
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input',
            'id': 'updateExistingClasses'
        })
    )
    
    # Field to select which classes to update
    class_update_fields = forms.MultipleChoiceField(
        required=False,
        label='Fields to Update in Classes',
        help_text='Select which fields should be updated in existing classes',
        widget=forms.CheckboxSelectMultiple(attrs={
            'class': 'form-check-input'
        }),
        choices=[
            ('teacher', 'Teacher'),
            ('start_time', 'Start Time'),
            ('duration_minutes', 'Duration'),
            ('facility', 'Facility'),
            ('classroom', 'Classroom'),
        ]
    )
    
    # Date range for selective updates
    update_classes_from_date = forms.DateField(
        required=False,
        label='Update Classes From Date',
        help_text='Only update classes from this date onwards (leave blank for all)',
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    def __init__(self, *args, **kwargs):
        self.instance = kwargs.get('instance')
        super().__init__(*args, **kwargs)
        
        if self.instance and self.instance.pk:
            # Set default date to today for future updates
            from django.utils import timezone
            self.fields['update_classes_from_date'].initial = timezone.now().date()
            
            # Pre-select commonly changed fields
            self.fields['class_update_fields'].initial = ['teacher', 'classroom']
    
    def clean(self):
        cleaned_data = super().clean()
        update_existing = cleaned_data.get('update_existing_classes')
        update_fields = cleaned_data.get('class_update_fields')
        
        if update_existing and not update_fields:
            self.add_error('class_update_fields', 
                          'Please select which fields to update in existing classes.')
        
        return cleaned_data


class ClassForm(forms.ModelForm):
    """Class form with Bootstrap styling"""
    
    class Meta:
        model = Class
        fields = [
            'course', 'date', 'start_time', 'duration_minutes',
            'teacher', 'facility', 'classroom', 'is_active'
        ]
        widgets = {
            'course': forms.Select(attrs={
                'class': 'form-select'
            }),
            'date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'start_time': forms.TimeInput(attrs={
                'class': 'form-control',
                'type': 'time'
            }),
            'duration_minutes': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '15',
                'step': '15'
            }),
            'teacher': forms.Select(attrs={
                'class': 'form-select'
            }),
            'facility': forms.Select(attrs={
                'class': 'form-select'
            }),
            'classroom': forms.Select(attrs={
                'class': 'form-select'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }