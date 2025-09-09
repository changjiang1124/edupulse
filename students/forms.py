from django import forms
from .models import Student, StudentTag


class StudentForm(forms.ModelForm):
    """Student form with Bootstrap styling - aligned with enrollment form"""
    
    class Meta:
        model = Student
        fields = [
            # Basic Information
            'first_name', 'last_name', 'birth_date', 'address',
            # Contact Information (unified)
            'contact_email', 'contact_phone',
            # Guardian Information
            'guardian_name',
            # Emergency Contact
            'emergency_contact_name', 'emergency_contact_phone',
            # Medical & Special Requirements
            'medical_conditions', 'special_requirements',
            # Reference & Management
            'reference', 'registration_status', 'enrollment_source',
            # Staff Fields
            'staff_notes', 'tags', 'is_active'
        ]
        widgets = {
            # Basic Information
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
            'address': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Enter full residential address',
                'rows': 3
            }),
            
            # Contact Information (unified)
            'contact_email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'contact@email.com'
            }),
            'contact_phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '0412 345 678'
            }),
            
            # Guardian Information
            'guardian_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Guardian full name (required for under 18)'
            }),
            
            # Emergency Contact
            'emergency_contact_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Emergency contact name'
            }),
            'emergency_contact_phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '0412 345 678'
            }),
            
            # Medical & Special Requirements
            'medical_conditions': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Any medical conditions we should be aware of',
                'rows': 3
            }),
            'special_requirements': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Any special requirements or accommodations needed',
                'rows': 3
            }),
            
            # Reference & Management
            'reference': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'How did you hear about us?'
            }),
            'registration_status': forms.Select(attrs={
                'class': 'form-select'
            }),
            'enrollment_source': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Where/how the student enrolled'
            }),
            
            # Staff Fields
            'staff_notes': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Internal notes for staff/teachers only',
                'rows': 4
            }),
            'tags': forms.CheckboxSelectMultiple(attrs={
                'class': 'form-check-input'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }
        
        help_texts = {
            'contact_email': 'Primary email address for communications (student or guardian depending on age)',
            'contact_phone': 'Primary phone number for SMS notifications (student or guardian depending on age)',
            'guardian_name': 'Required for students under 18 years of age',
            'medical_conditions': 'Any medical conditions we should be aware of',
            'special_requirements': 'Any special requirements or accommodations needed',
            'staff_notes': 'Internal notes for staff/teachers only (not visible to students)',
            'enrollment_source': 'Where/how the student enrolled (e.g., website, referral)',
        }
    
    def clean(self):
        """Validate student form data, especially guardian requirements for minors"""
        cleaned_data = super().clean()
        birth_date = cleaned_data.get('birth_date')
        guardian_name = cleaned_data.get('guardian_name')
        
        if birth_date:
            from datetime import date
            today = date.today()
            age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
            
            # Store calculated age for use in templates or other validation
            cleaned_data['calculated_age'] = age
            
            if age < 18:
                # Student is under 18, guardian name is required
                if not guardian_name or guardian_name.strip() == '':
                    self.add_error('guardian_name', 'Guardian name is required for students under 18 years of age.')
        
        return cleaned_data


class StudentTagForm(forms.ModelForm):
    """Student tag management form"""
    
    class Meta:
        model = StudentTag
        fields = ['name', 'colour', 'description', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter tag name'
            }),
            'colour': forms.TextInput(attrs={
                'class': 'form-control',
                'type': 'color',
                'placeholder': '#007bff'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Enter tag description',
                'rows': 3
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }


class BulkNotificationForm(forms.Form):
    """Form for sending bulk notifications to students"""
    
    NOTIFICATION_TYPE_CHOICES = [
        ('email', 'Email'),
        ('sms', 'SMS'),
        ('both', 'Both Email & SMS'),
    ]
    
    MESSAGE_TYPE_CHOICES = [
        ('general', 'General Message'),
        ('course_reminder', 'Course Reminder'),
        ('attendance_notice', 'Attendance Notice'),
        ('welcome', 'Welcome Message'),
        ('enrollment_confirm', 'Enrollment Confirmation'),
    ]
    
    SEND_TO_CHOICES = [
        ('selected', 'Selected Students Only'),
        ('all_active', 'All Active Students'),
        ('by_tag', 'Students by Tag'),
        ('pending_enrollments', 'Students with Pending Enrollments'),
        ('recent_enrollments', 'Recently Enrolled Students (Last 30 Days)'),
    ]
    
    # Selection method
    send_to = forms.ChoiceField(
        choices=SEND_TO_CHOICES,
        label='Send To',
        widget=forms.Select(attrs={
            'class': 'form-select',
            'onchange': 'handleSendToChange(this.value)'
        }),
        initial='selected'
    )
    
    # Student selection (hidden field populated by JavaScript)
    student_ids = forms.CharField(
        widget=forms.HiddenInput(),
        required=False
    )
    
    # Tag selection for 'by_tag' option
    selected_tags = forms.ModelMultipleChoiceField(
        queryset=StudentTag.objects.filter(is_active=True),
        widget=forms.CheckboxSelectMultiple(attrs={
            'class': 'form-check-input'
        }),
        required=False,
        label='Select Tags'
    )
    
    # Notification type
    notification_type = forms.ChoiceField(
        choices=NOTIFICATION_TYPE_CHOICES,
        label='Notification Type',
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    
    # Message categorization
    message_type = forms.ChoiceField(
        choices=MESSAGE_TYPE_CHOICES,
        label='Message Type',
        widget=forms.Select(attrs={
            'class': 'form-select'
        }),
        help_text='This helps categorize the message for reporting purposes'
    )
    
    # Email specific fields
    subject = forms.CharField(
        max_length=200,
        label='Email Subject',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter email subject'
        }),
        required=False
    )
    
    # Message content
    message = forms.CharField(
        label='Message Content',
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 6,
            'placeholder': 'Enter your message here...'
        }),
        help_text='This content will be used for both email body and SMS text'
    )
    
    def clean(self):
        cleaned_data = super().clean()
        notification_type = cleaned_data.get('notification_type')
        subject = cleaned_data.get('subject')
        message = cleaned_data.get('message')
        student_ids = cleaned_data.get('student_ids')
        send_to = cleaned_data.get('send_to')
        selected_tags = cleaned_data.get('selected_tags')
        
        errors = {}
        
        # Validate recipient selection
        if send_to == 'selected':
            if not student_ids or not student_ids.strip():
                errors['student_ids'] = 'At least one student must be selected'
            else:
                try:
                    student_id_list = [int(id.strip()) for id in student_ids.split(',') if id.strip()]
                    if not student_id_list:
                        errors['student_ids'] = 'At least one student must be selected'
                    cleaned_data['student_id_list'] = student_id_list
                except ValueError:
                    errors['student_ids'] = 'Invalid student selection'
        elif send_to == 'by_tag':
            if not selected_tags:
                errors['selected_tags'] = 'At least one tag must be selected when sending by tag'
        
        # Email specific validation
        if notification_type in ['email', 'both']:
            if not subject or not subject.strip():
                errors['subject'] = 'Email subject is required when sending emails'
        
        # Message length validation for SMS
        if notification_type in ['sms', 'both']:
            if len(message) > 160:
                errors['message'] = f'SMS message is too long ({len(message)} characters). Maximum 160 characters allowed.'
        
        # Raise all errors at once
        if errors:
            from django.core.exceptions import ValidationError
            raise ValidationError(errors)
        
        return cleaned_data