from django import forms
from .models import Student


class StudentForm(forms.ModelForm):
    """Student form with Bootstrap styling"""
    
    class Meta:
        model = Student
        fields = [
            'first_name', 'last_name', 'birth_date', 'email', 'phone', 'address',
            'guardian_name', 'guardian_phone', 'guardian_email', 'reference', 'is_active'
        ]
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter first name'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter last name'
            }),
            'birth_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'student@email.com'
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '0412 345 678'
            }),
            'address': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Enter full address',
                'rows': 3
            }),
            'guardian_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Guardian full name'
            }),
            'guardian_phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '0412 345 678'
            }),
            'guardian_email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'guardian@email.com'
            }),
            'reference': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'How did you hear about us?'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }