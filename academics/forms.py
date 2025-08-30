from django import forms
from tinymce.widgets import TinyMCE
from .models import Course, Class


class CourseForm(forms.ModelForm):
    """Course form with Bootstrap styling"""
    
    class Meta:
        model = Course
        fields = [
            'name', 'short_description', 'description', 'price', 'course_type', 'status', 'teacher',
            'start_date', 'end_date', 'repeat_pattern', 'start_time', 'duration_minutes',
            'vacancy', 'facility', 'classroom', 'is_bookable', 'is_active'
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
            'start_time': forms.TimeInput(attrs={
                'class': 'form-control',
                'type': 'time'
            }),
            'duration_minutes': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '15',
                'step': '15'
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
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }


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