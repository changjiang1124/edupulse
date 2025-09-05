from django import forms
from .models import Facility, Classroom


class FacilityForm(forms.ModelForm):
    """Facility form with Bootstrap styling and GPS integration"""
    
    class Meta:
        model = Facility
        fields = ['name', 'address', 'phone', 'email', 'latitude', 'longitude', 'attendance_radius', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter facility name'
            }),
            'address': forms.TextInput(attrs={
                'class': 'form-control',
                'id': 'address-autocomplete',
                'placeholder': 'Start typing address for suggestions...',
                'autocomplete': 'street-address',
                'data-lpignore': 'true',
                'data-1p-ignore': 'true'
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '+61 xxx xxx xxx'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'facility@email.com'
            }),
            'latitude': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': 'any',
                'placeholder': 'e.g. -31.9794'
            }),
            'longitude': forms.NumberInput(attrs={
                'class': 'form-control', 
                'step': 'any',
                'placeholder': 'e.g. 115.7799'
            }),
            'attendance_radius': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '10',
                'max': '500',
                'value': '50'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }


class ClassroomForm(forms.ModelForm):
    """Classroom form with Bootstrap styling"""
    
    class Meta:
        model = Classroom
        fields = ['facility', 'name', 'capacity', 'is_active']
        widgets = {
            'facility': forms.Select(attrs={
                'class': 'form-select'
            }),
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter classroom name or number'
            }),
            'capacity': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1',
                'max': '100',
                'placeholder': 'Maximum number of students'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Only show active facilities
        self.fields['facility'].queryset = Facility.objects.filter(is_active=True)
        
        # Set field labels
        self.fields['facility'].label = 'Facility *'
        self.fields['name'].label = 'Classroom Name/Number *'
        self.fields['capacity'].label = 'Capacity *'
        self.fields['is_active'].label = 'Active Classroom'
        
        # Set help text
        self.fields['name'].help_text = 'Room name, number, or identifier'
        self.fields['capacity'].help_text = 'Maximum number of students this classroom can accommodate'