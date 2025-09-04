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
    """Public enrollment form for students/guardians with age-based dynamic fields"""
    
    # Student Identification
    student_status = forms.ChoiceField(
        choices=[
            ('', 'Please select...'),
            ('new', 'New Student (First time enrolling)'),
            ('returning', 'Returning Student (Previously enrolled)')
        ],
        label='Student Status',
        widget=forms.Select(attrs={
            'class': 'form-select',
            'id': 'id_student_status'
        }),
        help_text='Are you enrolling for the first time or returning?'
    )
    
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
    
    date_of_birth = forms.DateField(
        label='Date of Birth',
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        help_text='Used for student identification and determining contact requirements'
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
    
    # Contact Information (unified - will be labeled dynamically based on age)
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
        help_text='Primary contact phone number for SMS notifications'
    )
    
    # Guardian Information (only for students under 18)
    guardian_name = forms.CharField(
        required=False,
        max_length=100,
        label='Parent/Guardian Name',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Full name of parent or guardian'
        }),
        help_text='Required for students under 18 years of age'
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
        # Populate course choices with pricing information
        courses = Course.objects.filter(status='published').order_by('name')
        course_choices = [('', 'Select a course...')]
        
        for course in courses:
            course_fee = f"${course.price}"
            if course.has_registration_fee():
                reg_fee_info = f" (+${course.registration_fee} registration fee for new students)"
            else:
                reg_fee_info = ""
            
            choice_label = f"{course.name} - {course_fee}{reg_fee_info}"
            course_choices.append((course.pk, choice_label))
        
        self.fields['course_id'].choices = course_choices
    
    def clean(self):
        cleaned_data = super().clean()
        date_of_birth = cleaned_data.get('date_of_birth')
        guardian_name = cleaned_data.get('guardian_name')
        student_status = cleaned_data.get('student_status')
        first_name = cleaned_data.get('first_name')
        last_name = cleaned_data.get('last_name')
        
        if date_of_birth:
            from datetime import date
            today = date.today()
            age = today.year - date_of_birth.year - ((today.month, today.day) < (date_of_birth.month, date_of_birth.day))
            
            # Store calculated age for use in views/templates
            cleaned_data['calculated_age'] = age
            
            if age < 18:
                # Student is under 18, guardian name is required
                if not guardian_name or guardian_name.strip() == '':
                    self.add_error('guardian_name', 'Guardian name is required for students under 18.')
        
        # Validate student status selection
        if not student_status:
            self.add_error('student_status', 'Please select if you are a new or returning student.')
        
        # Check for existing student if returning student is selected
        if student_status == 'returning' and first_name and last_name and date_of_birth:
            from students.services import StudentMatchingService
            existing_student, match_type = StudentMatchingService.find_existing_student({
                'first_name': first_name,
                'last_name': last_name,
                'date_of_birth': date_of_birth
            })
            
            if not existing_student or match_type == 'none':
                self.add_error('student_status', 
                    'No matching student record found. Please select "New Student" or verify the name and date of birth are correct.')
            elif match_type == 'multiple_matches':
                self.add_error('student_status', 
                    'Multiple students found with this name. Please contact us directly for enrollment.')
            else:
                # Store matched student for use in views
                cleaned_data['matched_student'] = existing_student
                cleaned_data['match_type'] = match_type
        
        return cleaned_data
    
    def get_student_age(self):
        """Helper method to calculate student age"""
        if hasattr(self, 'cleaned_data') and self.cleaned_data.get('date_of_birth'):
            from datetime import date
            birth_date = self.cleaned_data['date_of_birth']
            today = date.today()
            return today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
        return None