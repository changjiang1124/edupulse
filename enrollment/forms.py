from django import forms
from .models import Enrollment
from students.models import Student
from academics.models import Course


class EnrollmentForm(forms.ModelForm):
    """Enrollment form with Bootstrap styling"""
    
    class Meta:
        model = Enrollment
        fields = ['student', 'course', 'status', 'source_channel']
        widgets = {
            'student': forms.Select(attrs={
                'class': 'form-select'
            }),
            'course': forms.Select(attrs={
                'class': 'form-select'
            }),
            'status': forms.Select(attrs={
                'class': 'form-select'
            }),
            'source_channel': forms.Select(attrs={
                'class': 'form-select'
            }),
        }


class PublicEnrollmentForm(forms.Form):
    """Public enrollment form for students/guardians"""
    
    # Student Information
    first_name = forms.CharField(
        max_length=30,
        label='First Name',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Student\'s first name'
        })
    )
    
    last_name = forms.CharField(
        max_length=30,
        label='Last Name',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Student\'s last name'
        })
    )
    
    email = forms.EmailField(
        label='Contact Email Address',
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Primary contact email'
        }),
        help_text='This will be the main contact email for enrollment communications'
    )
    
    phone = forms.CharField(
        max_length=20,
        label='Contact Phone Number',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '0412 345 678'
        }),
        help_text='Primary contact phone number'
    )
    
    date_of_birth = forms.DateField(
        label='Date of Birth',
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    address = forms.CharField(
        required=False,
        label='Address',
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Full residential address'
        })
    )
    
    # Guardian Information (for minors)
    guardian_name = forms.CharField(
        required=False,
        max_length=100,
        label='Guardian/Parent Name',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Full name of parent or guardian'
        })
    )
    
    guardian_email = forms.EmailField(
        required=False,
        label='Guardian Email',
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'guardian@example.com'
        })
    )
    
    guardian_phone = forms.CharField(
        required=False,
        max_length=20,
        label='Guardian Phone',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '0412 345 678'
        })
    )
    
    # Emergency Contact
    emergency_contact_name = forms.CharField(
        required=False,
        max_length=100,
        label='Emergency Contact Name',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Emergency contact person'
        })
    )
    
    emergency_contact_phone = forms.CharField(
        required=False,
        max_length=20,
        label='Emergency Contact Phone',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '0412 345 678'
        })
    )
    
    # Medical & Special Requirements
    medical_conditions = forms.CharField(
        required=False,
        label='Medical Conditions',
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Any medical conditions we should be aware of'
        })
    )
    
    special_requirements = forms.CharField(
        required=False,
        label='Special Requirements',
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Any special requirements or accommodations needed'
        })
    )
    
    # Course Selection
    course_id = forms.ChoiceField(
        label='Course',
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Populate course choices
        courses = Course.objects.filter(status='published').order_by('name')
        self.fields['course_id'].choices = [('', 'Select a course...')] + [
            (course.pk, f"{course.name} - ${course.price}") for course in courses
        ]
    
    def clean(self):
        cleaned_data = super().clean()
        date_of_birth = cleaned_data.get('date_of_birth')
        guardian_name = cleaned_data.get('guardian_name')
        
        if date_of_birth:
            from datetime import date
            today = date.today()
            age = today.year - date_of_birth.year - ((today.month, today.day) < (date_of_birth.month, date_of_birth.day))
            
            if age < 18:
                # Student is under 18, guardian name is required
                if not guardian_name:
                    self.add_error('guardian_name', 'Guardian name is required for students under 18.')
        
        return cleaned_data