from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import Staff


class StaffForm(forms.ModelForm):
    """Staff form with Bootstrap styling"""
    
    class Meta:
        model = Staff
        fields = [
            'username', 'first_name', 'last_name', 'email', 'phone', 'role', 'is_active_staff'
        ]
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter username'
            }),
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter first name'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter last name'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'staff@perthartschool.com.au'
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '0412 345 678'
            }),
            'role': forms.Select(attrs={
                'class': 'form-select'
            }),
            'is_active_staff': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }


class StaffCreationForm(UserCreationForm):
    """Staff creation form with Bootstrap styling"""
    
    class Meta(UserCreationForm.Meta):
        model = Staff
        fields = UserCreationForm.Meta.fields + ('first_name', 'last_name', 'email', 'phone', 'role')
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add Bootstrap classes to all fields
        for field_name, field in self.fields.items():
            if field_name in ['password1', 'password2']:
                field.widget.attrs.update({'class': 'form-control'})
            elif field_name == 'role':
                field.widget.attrs.update({'class': 'form-select'})
            else:
                field.widget.attrs.update({'class': 'form-control'})