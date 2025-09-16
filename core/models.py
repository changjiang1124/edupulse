from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.core.mail import EmailMessage
from django.conf import settings
from accounts.models import Staff
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)


class OrganisationSettings(models.Model):
    """
    Organisation settings model - Singleton for global configuration
    """
    # Organisation Details
    organisation_name = models.CharField(
        max_length=200,
        default='Perth Art School',
        verbose_name='Organisation Name'
    )
    abn_number = models.CharField(
        max_length=20,
        blank=True,
        verbose_name='ABN Number',
        help_text='Australian Business Number'
    )
    
    # GST Configuration
    prices_include_gst = models.BooleanField(
        default=True,
        verbose_name='Prices Include GST',
        help_text='When enabled, all displayed prices include GST (10%). When disabled, GST will be added to displayed prices.'
    )
    gst_rate = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        default=Decimal('0.1000'),
        verbose_name='GST Rate',
        help_text='GST rate as decimal (e.g., 0.1000 for 10%)'
    )
    show_gst_breakdown = models.BooleanField(
        default=True,
        verbose_name='Show GST Breakdown',
        help_text='Display detailed GST breakdown in prices and confirmations'
    )
    gst_label = models.CharField(
        max_length=50,
        default='GST',
        verbose_name='GST Label',
        help_text='Label to use for GST (e.g., "GST", "Tax")'
    )
    
    # Contact Information
    contact_email = models.EmailField(
        default='info@perthartschool.com.au',
        verbose_name='Contact Email'
    )
    reply_to_email = models.EmailField(
        default='info@perthartschool.com.au',
        verbose_name='Reply-to Email Address',
        help_text='Default email address for recipients to reply to. Used when no specific reply-to is configured in email settings.'
    )
    contact_phone = models.CharField(
        max_length=20,
        default='(08) 9000 0000',
        verbose_name='Contact Phone'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        Staff,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Updated By'
    )
    
    class Meta:
        verbose_name = 'Organisation Setting'
        verbose_name_plural = 'Organisation Settings'
    
    def __str__(self):
        return f'{self.organisation_name} Settings'
    
    def clean(self):
        """Validate organisation settings"""
        super().clean()
        
        # Validate GST rate
        if self.gst_rate < 0 or self.gst_rate > 1:
            raise ValidationError('GST rate must be between 0 and 1 (e.g., 0.1 for 10%)')
    
    def save(self, *args, **kwargs):
        """Override save to ensure only one instance exists (singleton)"""
        if not self.pk and OrganisationSettings.objects.exists():
            raise ValidationError('Only one Organisation Settings instance is allowed')
        return super().save(*args, **kwargs)
    
    @classmethod
    def get_instance(cls):
        """Get the singleton instance, create if doesn't exist"""
        instance, created = cls.objects.get_or_create(
            id=1,
            defaults={
                'organisation_name': 'Perth Art School',
                'prices_include_gst': True,
                'gst_rate': Decimal('0.1000'),
                'show_gst_breakdown': True,
                'contact_email': 'info@perthartschool.com.au'
            }
        )
        return instance
    
    @classmethod
    def get_gst_config(cls):
        """Get GST configuration as dictionary with fixed Australian GST settings"""
        instance = cls.get_instance()
        return {
            'includes_gst': instance.prices_include_gst,
            'rate': Decimal('0.1000'),  # Fixed 10% GST for Australia
            'show_breakdown': False,    # Simplified - no breakdown display
            'label': 'GST'             # Fixed GST label
        }
    
    @property
    def gst_rate_percentage(self):
        """Get GST rate as percentage - fixed at 10% for Australia"""
        return 10


class EmailSettings(models.Model):
    """
    Email configuration settings - Singleton model for dynamic email configuration
    """
    BACKEND_CHOICES = [
        ('google_workspace', 'Google Workspace'),
        ('aws_ses', 'Amazon SES'),
        ('custom_smtp', 'Custom SMTP'),
    ]
    
    # Service type selection
    email_backend_type = models.CharField(
        max_length=20,
        choices=BACKEND_CHOICES,
        default='google_workspace',
        verbose_name='Email Service Type'
    )
    
    # SMTP Configuration
    smtp_host = models.CharField(
        max_length=255,
        default='smtp.gmail.com',
        verbose_name='SMTP Host'
    )
    smtp_port = models.PositiveIntegerField(
        default=587,
        verbose_name='SMTP Port'
    )
    smtp_username = models.EmailField(
        verbose_name='SMTP Username/Email'
    )
    smtp_password = models.CharField(
        max_length=255,
        verbose_name='SMTP Password/App Password',
        help_text='For Google Workspace, use App Password (not account password)'
    )
    use_tls = models.BooleanField(
        default=True,
        verbose_name='Use TLS Encryption'
    )
    
    # Sender Information
    from_email = models.EmailField(
        verbose_name='Default From Email'
    )
    from_name = models.CharField(
        max_length=100,
        default='Perth Art School',
        verbose_name='Default From Name'
    )
    reply_to_email = models.EmailField(
        blank=True,
        verbose_name='Reply-to Email Address',
        help_text='Email address for recipients to reply to. Leave blank to use from_email as reply-to'
    )
    
    # Configuration status
    is_active = models.BooleanField(
        default=False,
        verbose_name='Enable This Configuration',
        help_text='Only one configuration can be active at a time'
    )
    
    # Connection test results
    last_test_date = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Last Connection Test'
    )
    test_status = models.CharField(
        max_length=20,
        choices=[
            ('success', 'Success'),
            ('failed', 'Failed'),
            ('pending', 'Pending Test'),
        ],
        default='pending',
        verbose_name='Test Status'
    )
    test_message = models.TextField(
        blank=True,
        verbose_name='Test Result Message'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        Staff,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Updated By'
    )
    
    class Meta:
        verbose_name = 'Email Configuration'
        verbose_name_plural = 'Email Configurations'
        
    def __str__(self):
        return f'{self.get_email_backend_type_display()} ({self.smtp_username})'
    
    def clean(self):
        """Validate configuration"""
        super().clean()
        
        # Validate Google Workspace specific settings
        if self.email_backend_type == 'google_workspace':
            if not self.smtp_username.endswith('@gmail.com') and '@' not in self.smtp_username:
                raise ValidationError('Google Workspace requires a valid Gmail address')
            if self.smtp_host != 'smtp.gmail.com':
                self.smtp_host = 'smtp.gmail.com'
            if self.smtp_port != 587:
                self.smtp_port = 587
    
    def save(self, *args, **kwargs):
        """Override save to ensure only one active configuration"""
        if self.is_active:
            # Deactivate all other configurations
            EmailSettings.objects.exclude(pk=self.pk).update(is_active=False)
        
        super().save(*args, **kwargs)
    
    @classmethod
    def get_active_config(cls):
        """Get the currently active email configuration"""
        try:
            return cls.objects.get(is_active=True)
        except cls.DoesNotExist:
            return None
        except cls.MultipleObjectsReturned:
            # Fix corrupted data - only one should be active
            configs = cls.objects.filter(is_active=True)
            active_config = configs.first()
            configs.exclude(pk=active_config.pk).update(is_active=False)
            return active_config
    
    def test_connection(self):
        """Test SMTP connection with current settings"""
        try:
            # Create test email message
            from django.core.mail.backends.smtp import EmailBackend
            
            backend = EmailBackend(
                host=self.smtp_host,
                port=self.smtp_port,
                username=self.smtp_username,
                password=self.smtp_password,
                use_tls=self.use_tls,
                fail_silently=False
            )
            
            # Test connection by opening and closing
            connection = backend.open()
            if connection:
                backend.close()
                self.test_status = 'success'
                self.test_message = 'SMTP connection successful'
                self.last_test_date = timezone.now()
                logger.info(f'SMTP connection test successful for {self.smtp_username}')
                return True
            else:
                raise Exception('Failed to establish SMTP connection')
                
        except Exception as e:
            self.test_status = 'failed'
            self.test_message = str(e)
            self.last_test_date = timezone.now()
            logger.error(f'SMTP connection test failed for {self.smtp_username}: {e}')
            return False
        finally:
            self.save(update_fields=['test_status', 'test_message', 'last_test_date'])
    
    def send_test_email(self, recipient_email):
        """Send a test email to verify configuration"""
        try:
            from django.core.mail.backends.smtp import EmailBackend
            
            backend = EmailBackend(
                host=self.smtp_host,
                port=self.smtp_port,
                username=self.smtp_username,
                password=self.smtp_password,
                use_tls=self.use_tls,
                fail_silently=False
            )
            
            email = EmailMessage(
                subject='EduPulse Email Configuration Test',
                body=f'''This is a test email from EduPulse email configuration system.

Configuration Details:
- Service: {self.get_email_backend_type_display()}
- SMTP Host: {self.smtp_host}
- SMTP Port: {self.smtp_port}
- From: {self.from_name} <{self.from_email}>
- Test Time: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}

If you receive this email, your email configuration is working correctly.

Best regards,
Perth Art School EduPulse System''',
                from_email=f'{self.from_name} <{self.from_email}>',
                to=[recipient_email],
                reply_to=[self.reply_to_email or OrganisationSettings.get_instance().reply_to_email],
                connection=backend
            )
            
            email.send()
            logger.info(f'Test email sent successfully to {recipient_email} from {self.smtp_username}')
            return True
            
        except Exception as e:
            logger.error(f'Test email failed to {recipient_email} from {self.smtp_username}: {e}')
            raise e


class SMSSettings(models.Model):
    """
    SMS configuration settings - Singleton model for dynamic SMS configuration
    """
    BACKEND_CHOICES = [
        ('twilio', 'Twilio SMS'),
        ('custom_sms', 'Custom SMS Gateway'),
    ]
    
    # Service type selection
    sms_backend_type = models.CharField(
        max_length=20,
        choices=BACKEND_CHOICES,
        default='twilio',
        verbose_name='SMS Service Type'
    )
    
    # Twilio Configuration
    account_sid = models.CharField(
        max_length=255,
        verbose_name='Account SID',
        help_text='Twilio Account SID'
    )
    auth_token = models.CharField(
        max_length=255,
        verbose_name='Auth Token',
        help_text='Twilio Auth Token'
    )
    from_number = models.CharField(
        max_length=20,
        verbose_name='From Phone Number',
        help_text='Twilio phone number in E.164 format (e.g., +61400123456)'
    )
    
    # Custom SMS Gateway Configuration (for future use)
    api_url = models.URLField(
        blank=True,
        verbose_name='API URL',
        help_text='Custom SMS gateway API endpoint'
    )
    api_key = models.CharField(
        max_length=255,
        blank=True,
        verbose_name='API Key',
        help_text='Custom SMS gateway API key'
    )
    
    # Sender Information
    sender_name = models.CharField(
        max_length=11,  # SMS sender ID limit
        default='PerthArt',
        verbose_name='Sender Name',
        help_text='SMS sender name (max 11 characters for alphanumeric)'
    )
    
    # Configuration status
    is_active = models.BooleanField(
        default=False,
        verbose_name='Enable This Configuration',
        help_text='Only one configuration can be active at a time'
    )
    
    # Connection test results
    last_test_date = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Last Connection Test'
    )
    test_status = models.CharField(
        max_length=20,
        choices=[
            ('success', 'Success'),
            ('failed', 'Failed'),
            ('pending', 'Pending Test'),
        ],
        default='pending',
        verbose_name='Test Status'
    )
    test_message = models.TextField(
        blank=True,
        verbose_name='Test Result Message'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        Staff,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Updated By'
    )
    
    class Meta:
        verbose_name = 'SMS Configuration'
        verbose_name_plural = 'SMS Configurations'
        
    def __str__(self):
        return f'{self.get_sms_backend_type_display()} ({self.from_number})'
    
    def clean(self):
        """Validate configuration"""
        super().clean()
        
        # Validate Twilio specific settings
        if self.sms_backend_type == 'twilio':
            if not self.account_sid:
                raise ValidationError('Account SID is required for Twilio')
            if not self.auth_token:
                raise ValidationError('Auth Token is required for Twilio')
            if not self.from_number:
                raise ValidationError('From Number is required for Twilio')
            # Validate phone number format (basic E.164 check)
            if not self.from_number.startswith('+'):
                raise ValidationError('Phone number must be in E.164 format (start with +)')
    
    def save(self, *args, **kwargs):
        """Override save to ensure only one active configuration"""
        if self.is_active:
            # Deactivate all other configurations
            SMSSettings.objects.exclude(pk=self.pk).update(is_active=False)
        
        super().save(*args, **kwargs)
    
    @classmethod
    def get_active_config(cls):
        """Get the currently active SMS configuration"""
        try:
            return cls.objects.get(is_active=True)
        except cls.DoesNotExist:
            return None
        except cls.MultipleObjectsReturned:
            # Fix corrupted data - only one should be active
            configs = cls.objects.filter(is_active=True)
            active_config = configs.first()
            configs.exclude(pk=active_config.pk).update(is_active=False)
            return active_config
    
    def test_connection(self):
        """Test SMS connection with current settings"""
        try:
            if self.sms_backend_type == 'twilio':
                from twilio.rest import Client
                
                client = Client(self.account_sid, self.auth_token)
                
                # Test by fetching account info
                account = client.api.account.fetch()
                
                if account.status == 'active':
                    self.test_status = 'success'
                    self.test_message = f'Twilio connection successful. Account: {account.friendly_name}'
                    self.last_test_date = timezone.now()
                    logger.info(f'Twilio connection test successful for {self.from_number}')
                    return True
                else:
                    raise Exception(f'Twilio account status: {account.status}')
                    
        except ImportError:
            self.test_status = 'failed'
            self.test_message = 'Twilio library not installed. Please install: pip install twilio'
            self.last_test_date = timezone.now()
            logger.error('Twilio library not installed')
            return False
        except Exception as e:
            self.test_status = 'failed'
            self.test_message = str(e)
            self.last_test_date = timezone.now()
            logger.error(f'SMS connection test failed for {self.from_number}: {e}')
            return False
        finally:
            self.save(update_fields=['test_status', 'test_message', 'last_test_date'])
    
    def send_test_sms(self, recipient_phone):
        """Send a test SMS to verify configuration"""
        try:
            if self.sms_backend_type == 'twilio':
                from twilio.rest import Client
                
                client = Client(self.account_sid, self.auth_token)
                
                message = client.messages.create(
                    body=f'''Test SMS from EduPulse SMS system.

Configuration: {self.get_sms_backend_type_display()}
From: {self.sender_name}
Time: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}

If you receive this message, your SMS configuration is working correctly.

Perth Art School EduPulse System''',
                    from_=self.from_number,
                    to=recipient_phone
                )
                
                logger.info(f'Test SMS sent successfully to {recipient_phone} from {self.from_number}. Message SID: {message.sid}')
                return True
                
        except ImportError:
            logger.error('Twilio library not installed')
            raise Exception('Twilio library not installed. Please install: pip install twilio')
        except Exception as e:
            logger.error(f'Test SMS failed to {recipient_phone} from {self.from_number}: {e}')
            raise e


class ClockInOut(models.Model):
    """
    Staff clock in/out model
    """
    STATUS_CHOICES = [
        ('clock_in', 'Clock In'),
        ('clock_out', 'Clock Out'),
    ]
    
    staff = models.ForeignKey(
        Staff,
        on_delete=models.CASCADE,
        related_name='clock_records',
        verbose_name='Staff Member'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        verbose_name='Clock Status'
    )
    timestamp = models.DateTimeField(
        default=timezone.now,
        verbose_name='Clock Time'
    )
    
    # GPS location record
    latitude = models.DecimalField(
        max_digits=10,
        decimal_places=8,
        null=True,
        blank=True,
        verbose_name='Latitude'
    )
    longitude = models.DecimalField(
        max_digits=11,
        decimal_places=8,
        null=True,
        blank=True,
        verbose_name='Longitude'
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Created At'
    )
    
    class Meta:
        verbose_name = 'Clock Record'
        verbose_name_plural = 'Clock Records'
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.staff.get_full_name()} - {self.get_status_display()} at {self.timestamp.strftime('%Y-%m-%d %H:%M')}"


class TeacherAttendance(models.Model):
    """
    Teacher attendance model for GPS-based clock in/out system
    """
    CLOCK_TYPE_CHOICES = [
        ('clock_in', 'Clock In'),
        ('clock_out', 'Clock Out'),
    ]
    
    teacher = models.ForeignKey(
        Staff,
        on_delete=models.CASCADE,
        related_name='teacher_attendance',
        verbose_name='Teacher',
        limit_choices_to={'role': 'teacher'}
    )
    clock_type = models.CharField(
        max_length=20,
        choices=CLOCK_TYPE_CHOICES,
        verbose_name='Clock Type'
    )
    timestamp = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Clock Time'
    )
    
    # Associated classes (many-to-many as teacher can select multiple classes)
    classes = models.ManyToManyField(
        'academics.Class',
        blank=True,
        verbose_name='Associated Classes',
        help_text='Classes that this attendance record is for'
    )
    
    # Location verification
    facility = models.ForeignKey(
        'facilities.Facility',
        on_delete=models.CASCADE,
        verbose_name='Facility',
        help_text='Facility where attendance was recorded'
    )
    latitude = models.DecimalField(
        max_digits=10,
        decimal_places=8,
        verbose_name='Teacher Latitude',
        help_text='GPS latitude where teacher clocked in/out'
    )
    longitude = models.DecimalField(
        max_digits=11,
        decimal_places=8,
        verbose_name='Teacher Longitude',
        help_text='GPS longitude where teacher clocked in/out'
    )
    distance_from_facility = models.FloatField(
        verbose_name='Distance from Facility (meters)',
        help_text='Calculated distance from facility location'
    )
    location_verified = models.BooleanField(
        default=False,
        verbose_name='Location Verified',
        help_text='Whether location is within acceptable range'
    )
    
    # Additional tracking information
    ip_address = models.GenericIPAddressField(
        verbose_name='IP Address'
    )
    user_agent = models.TextField(
        blank=True,
        verbose_name='User Agent',
        help_text='Browser/device information'
    )
    notes = models.TextField(
        blank=True,
        verbose_name='Notes',
        help_text='Additional notes or comments'
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Created At'
    )
    
    class Meta:
        verbose_name = 'Teacher Attendance'
        verbose_name_plural = 'Teacher Attendance Records'
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.teacher.get_full_name()} - {self.get_clock_type_display()} at {self.facility.name} ({self.timestamp.strftime('%Y-%m-%d %H:%M')})"


class EmailLog(models.Model):
    """
    Email log model
    """
    STATUS_CHOICES = [
        ('sent', 'Sent'),
        ('failed', 'Failed'),
    ]
    
    TYPE_CHOICES = [
        ('welcome', 'Welcome Email'),
        ('enrollment_confirm', 'Enrolment Confirmation'),
        ('attendance_notice', 'Attendance Notice'),
        ('course_reminder', 'Course Reminder'),
        ('test', 'Test Email'),
        ('general', 'General Email'),
    ]
    
    recipient_email = models.EmailField(
        verbose_name='Recipient Email'
    )
    recipient_type = models.CharField(
        max_length=20,
        choices=[('student', 'Student'), ('staff', 'Staff'), ('guardian', 'Guardian')],
        verbose_name='Recipient Type'
    )
    subject = models.CharField(
        max_length=200,
        verbose_name='Email Subject'
    )
    content = models.TextField(
        verbose_name='Email Content'
    )
    email_type = models.CharField(
        max_length=30,
        choices=TYPE_CHOICES,
        verbose_name='Email Type'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='sent',
        verbose_name='Send Status'
    )
    error_message = models.TextField(
        blank=True,
        verbose_name='Error Message'
    )
    email_backend = models.CharField(
        max_length=50,
        default='unknown',
        verbose_name='Email Backend'
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Send Time'
    )
    sent_at = models.DateTimeField(
        null=True, 
        blank=True,
        verbose_name='Sent At'  # Alias for compatibility with template
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Updated At'
    )
    
    class Meta:
        verbose_name = 'Email Log'
        verbose_name_plural = 'Email Logs'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.recipient_email} - {self.subject} ({self.get_status_display()})"


class SMSLog(models.Model):
    """
    SMS log model
    """
    STATUS_CHOICES = [
        ('sent', 'Sent'),
        ('failed', 'Failed'),
    ]
    
    TYPE_CHOICES = [
        ('welcome', 'Welcome SMS'),
        ('enrollment_confirm', 'Enrolment Confirmation'),
        ('attendance_notice', 'Attendance Notice'),
        ('course_reminder', 'Course Reminder'),
        ('test', 'Test SMS'),
        ('general', 'General SMS'),
    ]
    
    recipient_phone = models.CharField(
        max_length=20,
        verbose_name='Recipient Phone'
    )
    recipient_type = models.CharField(
        max_length=20,
        choices=[('student', 'Student'), ('staff', 'Staff'), ('guardian', 'Guardian')],
        verbose_name='Recipient Type'
    )
    content = models.TextField(
        verbose_name='SMS Content'
    )
    sms_type = models.CharField(
        max_length=30,
        choices=TYPE_CHOICES,
        verbose_name='SMS Type'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='sent',
        verbose_name='Send Status'
    )
    error_message = models.TextField(
        blank=True,
        verbose_name='Error Message'
    )
    message_sid = models.CharField(
        max_length=50,
        blank=True,
        verbose_name='Message SID',
        help_text='Twilio message SID for tracking'
    )
    backend_type = models.CharField(
        max_length=50,
        default='twilio',
        verbose_name='SMS Backend'
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Send Time'
    )
    sent_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Sent At'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Updated At'
    )
    
    class Meta:
        verbose_name = 'SMS Log'
        verbose_name_plural = 'SMS Logs'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.recipient_phone} - {self.get_sms_type_display()} ({self.get_status_display()})"


class NotificationQuota(models.Model):
    """
    Monthly notification quota management for SMS and Email
    """
    NOTIFICATION_TYPE_CHOICES = [
        ('email', 'Email'),
        ('sms', 'SMS'),
    ]
    
    # Quota configuration
    notification_type = models.CharField(
        max_length=10,
        choices=NOTIFICATION_TYPE_CHOICES,
        verbose_name='Notification Type'
    )
    year = models.PositiveIntegerField(
        verbose_name='Year'
    )
    month = models.PositiveIntegerField(
        choices=[(i, i) for i in range(1, 13)],
        verbose_name='Month'
    )
    monthly_limit = models.PositiveIntegerField(
        verbose_name='Monthly Limit',
        help_text='Maximum number of notifications allowed per month'
    )
    
    # Usage tracking
    used_count = models.PositiveIntegerField(
        default=0,
        verbose_name='Used Count',
        help_text='Number of notifications used this month'
    )
    
    # Administrative fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Notification Quota'
        verbose_name_plural = 'Notification Quotas'
        unique_together = ['notification_type', 'year', 'month']
        ordering = ['-year', '-month', 'notification_type']
    
    def __str__(self):
        return f'{self.get_notification_type_display()} {self.year}-{self.month:02d}: {self.used_count}/{self.monthly_limit}'
    
    @property
    def is_quota_exceeded(self):
        """Check if quota is exceeded"""
        return self.used_count >= self.monthly_limit
    
    @property
    def remaining_quota(self):
        """Get remaining quota"""
        return max(0, self.monthly_limit - self.used_count)
    
    @property
    def usage_percentage(self):
        """Get usage percentage"""
        if self.monthly_limit == 0:
            return 100
        return min(100, (self.used_count / self.monthly_limit) * 100)
    
    @classmethod
    def get_current_quota(cls, notification_type):
        """Get current month's quota for notification type"""
        from django.utils import timezone
        now = timezone.now()
        
        quota, created = cls.objects.get_or_create(
            notification_type=notification_type,
            year=now.year,
            month=now.month,
            defaults={'monthly_limit': 200}  # Default limit
        )
        return quota
    
    @classmethod
    def check_quota_available(cls, notification_type, count=1):
        """Check if quota is available for sending notifications"""
        quota = cls.get_current_quota(notification_type)
        return quota.remaining_quota >= count
    
    @classmethod
    def consume_quota(cls, notification_type, count=1):
        """Consume quota when notifications are sent"""
        quota = cls.get_current_quota(notification_type)
        quota.used_count = models.F('used_count') + count
        quota.save(update_fields=['used_count'])
        quota.refresh_from_db()
        return quota


class WooCommerceSyncLog(models.Model):
    """
    Log model for tracking WooCommerce synchronization activities
    """
    SYNC_TYPE_CHOICES = [
        ('create', 'Create Product'),
        ('update', 'Update Product'),
        ('delete', 'Delete Product'),
        ('category', 'Create/Update Category'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('retrying', 'Retrying'),
    ]
    
    # Basic information
    sync_type = models.CharField(
        max_length=20,
        choices=SYNC_TYPE_CHOICES,
        verbose_name='Sync Type'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name='Status'
    )
    
    # Course reference (nullable for category operations)
    course = models.ForeignKey(
        'academics.Course',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='sync_logs',
        verbose_name='Course'
    )
    course_name = models.CharField(
        max_length=200,
        blank=True,
        verbose_name='Course Name',
        help_text='Cached course name for reference'
    )
    
    # WooCommerce data
    wc_product_id = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='WooCommerce Product ID'
    )
    wc_category_id = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='WooCommerce Category ID'
    )
    wc_category_name = models.CharField(
        max_length=200,
        blank=True,
        verbose_name='WooCommerce Category Name'
    )
    
    # Sync results
    error_message = models.TextField(
        blank=True,
        verbose_name='Error Message'
    )
    response_data = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='Response Data',
        help_text='Raw response from WooCommerce API'
    )
    request_data = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='Request Data',
        help_text='Data sent to WooCommerce API'
    )
    
    # Retry and timing information
    retry_count = models.PositiveIntegerField(
        default=0,
        verbose_name='Retry Count'
    )
    max_retries = models.PositiveIntegerField(
        default=3,
        verbose_name='Max Retries'
    )
    duration_ms = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name='Duration (ms)',
        help_text='Time taken for the API call in milliseconds'
    )
    
    # Timestamps
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Created At'
    )
    last_attempt_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Last Attempt At'
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Completed At'
    )
    
    class Meta:
        verbose_name = 'WooCommerce Sync Log'
        verbose_name_plural = 'WooCommerce Sync Logs'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['course', 'sync_type']),
            models.Index(fields=['wc_product_id']),
        ]
    
    def __str__(self):
        if self.course:
            return f"{self.get_sync_type_display()} - {self.course.name} ({self.get_status_display()})"
        return f"{self.get_sync_type_display()} - Category {self.wc_category_name} ({self.get_status_display()})"
    
    def save(self, *args, **kwargs):
        # Cache course name for easier reference
        if self.course and not self.course_name:
            self.course_name = self.course.name
        
        # Set completed timestamp when status becomes success or failed (final states)
        if self.status in ['success', 'failed'] and not self.completed_at:
            self.completed_at = timezone.now()
        
        super().save(*args, **kwargs)
    
    @property
    def is_completed(self):
        """Check if sync is in final state"""
        return self.status in ['success', 'failed']
    
    @property
    def can_retry(self):
        """Check if sync can be retried"""
        return self.status == 'failed' and self.retry_count < self.max_retries
    
    @property
    def duration_display(self):
        """Human-friendly duration display"""
        if self.duration_ms is None:
            return "N/A"
        if self.duration_ms < 1000:
            return f"{self.duration_ms}ms"
        else:
            return f"{self.duration_ms / 1000:.1f}s"


class WooCommerceSyncQueue(models.Model):
    """
    Queue model for managing WooCommerce synchronization tasks
    """
    ACTION_CHOICES = [
        ('sync', 'Sync Product'),
        ('delete', 'Delete Product'),
        ('category_sync', 'Sync Category'),
    ]
    
    STATUS_CHOICES = [
        ('queued', 'Queued'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]
    
    PRIORITY_CHOICES = [
        (1, 'Critical'),
        (3, 'High'),
        (5, 'Normal'),
        (7, 'Low'),
        (9, 'Background'),
    ]
    
    # Task definition
    course = models.ForeignKey(
        'academics.Course',
        on_delete=models.CASCADE,
        related_name='sync_queue_items',
        verbose_name='Course'
    )
    action = models.CharField(
        max_length=20,
        choices=ACTION_CHOICES,
        verbose_name='Action'
    )
    priority = models.IntegerField(
        choices=PRIORITY_CHOICES,
        default=5,
        verbose_name='Priority'
    )
    
    # Scheduling
    scheduled_for = models.DateTimeField(
        default=timezone.now,
        verbose_name='Scheduled For'
    )
    
    # Status tracking
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='queued',
        verbose_name='Status'
    )
    attempts = models.PositiveIntegerField(
        default=0,
        verbose_name='Attempts'
    )
    max_retries = models.PositiveIntegerField(
        default=3,
        verbose_name='Max Retries'
    )
    
    # References
    sync_log = models.ForeignKey(
        WooCommerceSyncLog,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Related Sync Log'
    )
    
    # Error tracking
    last_error = models.TextField(
        blank=True,
        verbose_name='Last Error'
    )
    
    # Timestamps
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Created At'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Updated At'
    )
    started_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Started At'
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Completed At'
    )
    
    class Meta:
        verbose_name = 'WooCommerce Sync Queue Item'
        verbose_name_plural = 'WooCommerce Sync Queue'
        ordering = ['priority', 'scheduled_for']
        indexes = [
            models.Index(fields=['status', 'priority', 'scheduled_for']),
            models.Index(fields=['course', 'action']),
        ]
    
    def __str__(self):
        return f"{self.get_action_display()} - {self.course.name} ({self.get_status_display()})"
    
    def save(self, *args, **kwargs):
        # Set completed timestamp when status becomes completed, failed, or cancelled
        if self.status in ['completed', 'failed', 'cancelled'] and not self.completed_at:
            self.completed_at = timezone.now()
        
        # Set started timestamp when status becomes processing
        if self.status == 'processing' and not self.started_at:
            self.started_at = timezone.now()
        
        super().save(*args, **kwargs)
    
    @property
    def can_retry(self):
        """Check if queue item can be retried"""
        return self.status == 'failed' and self.attempts < self.max_retries
    
    @property
    def is_ready(self):
        """Check if queue item is ready for processing"""
        return (
            self.status == 'queued' and 
            self.scheduled_for <= timezone.now()
        )
    
    @property
    def duration_display(self):
        """Human-friendly duration display"""
        if not self.started_at or not self.completed_at:
            return "N/A"
        
        duration = self.completed_at - self.started_at
        total_seconds = duration.total_seconds()
        
        if total_seconds < 60:
            return f"{total_seconds:.1f}s"
        else:
            minutes = int(total_seconds // 60)
            seconds = int(total_seconds % 60)
            return f"{minutes}m {seconds}s"
