from django import forms
from django.core.exceptions import ValidationError
from .models import EmailSettings, SMSSettings


class EmailSettingsForm(forms.ModelForm):
    """Email configuration form with validation and presets"""
    
    test_email = forms.EmailField(
        required=False,
        label='Test Email Address',
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'admin@perthartschool.com.au'
        }),
        help_text='Enter an email address to receive test emails'
    )
    
    class Meta:
        model = EmailSettings
        fields = [
            'smtp_host', 'smtp_port', 'smtp_username', 
            'smtp_password', 'use_tls', 'from_email', 'from_name', 'reply_to_email', 'is_active'
        ]
        widgets = {
            'smtp_host': forms.TextInput(attrs={
                'class': 'form-control'
            }),
            'smtp_port': forms.NumberInput(attrs={
                'class': 'form-control'
            }),
            'smtp_username': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'your-email@example.com'
            }),
            'smtp_password': forms.PasswordInput(attrs={
                'class': 'form-control',
                'placeholder': 'Your email password or App Password'
            }),
            'use_tls': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'from_email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'noreply@perthartschool.com.au'
            }),
            'from_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Perth Art School'
            }),
            'reply_to_email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'reply@perthartschool.com.au'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['smtp_password'].help_text = (
            'For some providers like Google Workspace, you may need to use an App Password.'
        )

    def clean(self):
        cleaned_data = super().clean()
        # Enforce Google Workspace app password minimum length for security
        backend_type = self.data.get('email_backend_type')
        smtp_password = cleaned_data.get('smtp_password')
        if backend_type == 'google_workspace':
            if smtp_password and len(smtp_password) < 8:
                raise ValidationError({'smtp_password': 'App Password should be at least 8 characters'})
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.email_backend_type = 'smtp'  # Always set to smtp
        if commit:
            instance.save()
        return instance


class TestEmailForm(forms.Form):
    """Simple form for sending test emails"""
    
    recipient_email = forms.EmailField(
        label='Recipient Email',
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'test@example.com'
        }),
        help_text='Email address to receive the test email'
    )


class SMSSettingsForm(forms.ModelForm):
    """SMS configuration form with validation and presets"""
    
    test_phone = forms.CharField(
        required=False,
        label='Test Phone Number',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '+61400123456'
        }),
        help_text='Enter a phone number to receive test SMS (E.164 format)'
    )
    
    class Meta:
        model = SMSSettings
        fields = [
            'sms_backend_type', 'account_sid', 'auth_token', 'from_number',
            'api_url', 'api_key', 'sender_name', 'is_active'
        ]
        widgets = {
            'sms_backend_type': forms.Select(attrs={
                'class': 'form-select',
                'onchange': 'handleSMSBackendTypeChange(this.value)'
            }),
            'account_sid': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'
            }),
            'auth_token': forms.PasswordInput(attrs={
                'class': 'form-control',
                'placeholder': 'Your Twilio Auth Token'
            }),
            'from_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '+61400123456'
            }),
            'api_url': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://api.example.com/sms'
            }),
            'api_key': forms.PasswordInput(attrs={
                'class': 'form-control',
                'placeholder': 'Custom SMS API Key'
            }),
            'sender_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'PerthArt'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Add help text for Twilio
        self.fields['account_sid'].help_text = '''
        Your Twilio Account SID from the Twilio Console Dashboard.
        Format: ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
        '''
        
        self.fields['auth_token'].help_text = '''
        Your Twilio Auth Token from the Twilio Console Dashboard.
        Keep this secure and never share it publicly.
        '''
        
        self.fields['from_number'].help_text = '''
        Your Twilio phone number in E.164 format (e.g., +61400123456).
        This must be a valid Twilio number associated with your account.
        '''
        
        self.fields['sender_name'].help_text = '''
        Sender name for SMS messages (max 11 alphanumeric characters).
        Used when supported by the SMS gateway.
        '''
        
        # Set initial values based on backend type
        if self.instance and self.instance.sms_backend_type == 'custom_sms':
            self.fields['account_sid'].required = False
            self.fields['auth_token'].required = False
            self.fields['from_number'].required = False
        else:
            self.fields['api_url'].required = False
            self.fields['api_key'].required = False
    
    def clean_from_number(self):
        from_number = self.cleaned_data.get('from_number')
        if from_number and not from_number.startswith('+'):
            raise ValidationError('Phone number must be in E.164 format (start with +)')
        return from_number
    
    def clean_test_phone(self):
        test_phone = self.cleaned_data.get('test_phone')
        if test_phone and not test_phone.startswith('+'):
            raise ValidationError('Phone number must be in E.164 format (start with +)')
        return test_phone
    
    def clean(self):
        cleaned_data = super().clean()
        sms_backend_type = cleaned_data.get('sms_backend_type')
        account_sid = cleaned_data.get('account_sid')
        auth_token = cleaned_data.get('auth_token')
        from_number = cleaned_data.get('from_number')
        api_url = cleaned_data.get('api_url')
        api_key = cleaned_data.get('api_key')
        
        # Twilio specific validation
        if sms_backend_type == 'twilio':
            if not account_sid:
                raise ValidationError({'account_sid': 'Account SID is required for Twilio'})
            if not auth_token:
                raise ValidationError({'auth_token': 'Auth Token is required for Twilio'})
            if not from_number:
                raise ValidationError({'from_number': 'From Number is required for Twilio'})
            
            # Basic format validation
            if account_sid and not account_sid.startswith('AC'):
                raise ValidationError({'account_sid': 'Twilio Account SID should start with "AC"'})
        
        # Custom SMS gateway validation
        elif sms_backend_type == 'custom_sms':
            if not api_url:
                raise ValidationError({'api_url': 'API URL is required for custom SMS gateway'})
            if not api_key:
                raise ValidationError({'api_key': 'API Key is required for custom SMS gateway'})
        
        return cleaned_data


class TestSMSForm(forms.Form):
    """Simple form for sending test SMS"""
    
    recipient_phone = forms.CharField(
        label='Recipient Phone Number',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '+61400123456'
        }),
        help_text='Phone number to receive the test SMS (E.164 format)'
    )
    
    def clean_recipient_phone(self):
        recipient_phone = self.cleaned_data.get('recipient_phone')
        if not recipient_phone.startswith('+'):
            raise ValidationError('Phone number must be in E.164 format (start with +)')
        return recipient_phone


# Form mixins for consistent styling
class BootstrapFormMixin:
    """Mixin to apply Bootstrap classes to all form fields"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.update({'class': 'form-check-input'})
            elif isinstance(field.widget, forms.Select):
                field.widget.attrs.update({'class': 'form-select'})
            elif isinstance(field.widget, (forms.TextInput, forms.EmailInput, forms.NumberInput, 
                                         forms.DateInput, forms.TimeInput, forms.PasswordInput)):
                field.widget.attrs.update({'class': 'form-control'})
            elif isinstance(field.widget, forms.Textarea):
                field.widget.attrs.update({'class': 'form-control'})


class NotificationForm(forms.Form):
    """Form for sending notifications to students"""
    
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
    
    # Recipient selection (handled via JavaScript)
    student_ids = forms.CharField(
        widget=forms.HiddenInput(),
        required=True
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
        
        errors = {}
        
        # Validate student IDs
        if student_ids:
            try:
                student_id_list = [int(id.strip()) for id in student_ids.split(',') if id.strip()]
                if not student_id_list:
                    raise ValidationError('At least one student must be selected')
                cleaned_data['student_id_list'] = student_id_list
            except ValueError:
                raise ValidationError('Invalid student selection')
        else:
            raise ValidationError('At least one student must be selected')
        
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
            raise ValidationError(errors)
        
        return cleaned_data


class BulkNotificationForm(NotificationForm):
    """Extended form for bulk notifications with additional options"""
    
    SEND_TO_CHOICES = [
        ('selected', 'Selected Students Only'),
        ('all_active', 'All Active Students'),
        ('pending_enrollments', 'Students with Pending Enrollments'),
        ('recent_enrollments', 'Recently Enrolled Students (Last 30 Days)'),
    ]
    
    # Override parent field to make it not required for bulk sending
    student_ids = forms.CharField(
        widget=forms.HiddenInput(),
        required=False
    )
    
    send_to = forms.ChoiceField(
        choices=SEND_TO_CHOICES,
        label='Send To',
        widget=forms.Select(attrs={
            'class': 'form-select'
        }),
        initial='selected'
    )
    
    def clean(self):
        cleaned_data = super(NotificationForm, self).clean()  # Skip parent's clean method
        notification_type = cleaned_data.get('notification_type')
        subject = cleaned_data.get('subject')
        message = cleaned_data.get('message')
        student_ids = cleaned_data.get('student_ids')
        send_to = cleaned_data.get('send_to')
        
        errors = {}
        
        # Custom student ID validation for bulk forms
        if send_to == 'selected':
            if not student_ids or not student_ids.strip():
                raise ValidationError('Student selection is required when "Selected Students Only" is chosen')
            try:
                student_id_list = [int(id.strip()) for id in student_ids.split(',') if id.strip()]
                if not student_id_list:
                    raise ValidationError('At least one student must be selected')
                cleaned_data['student_id_list'] = student_id_list
            except ValueError:
                raise ValidationError('Invalid student selection')
        else:
            cleaned_data['student_id_list'] = []  # Will be populated in view
        
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
            raise ValidationError(errors)
        
        return cleaned_data
